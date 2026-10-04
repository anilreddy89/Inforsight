package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DataAccessException;
import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;

/** Gate the exact public routing surface before Spring decodes path variables. */
@Component
@Profile("persistence")
@ConditionalOnProperty(name="inforsight.journey.enabled",havingValue="true")
@Order(Ordered.HIGHEST_PRECEDENCE+10)
public class DemoSessionFilter extends OncePerRequestFilter {
    private static final Pattern RUN=Pattern.compile("^/api/v1/demo/runs/([A-Za-z0-9_-]{1,96})(?:/(retry|decision|audit))?$");
    private final DemoPublicAccess access;private final ObjectMapper mapper;
    public DemoSessionFilter(DemoPublicAccess access,ObjectMapper mapper){this.access=access;this.mapper=mapper;}
    @Override protected boolean shouldNotFilter(HttpServletRequest request){
        String raw=request.getRequestURI();
        // Do not let encoded path segments select a Spring route while skipping
        // this filter. Public mode also closes the unrelated legacy API surface.
        return !access.enabled()||!(raw.startsWith("/api")||raw.contains("%")||request.getServletPath().startsWith("/api"));
    }
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)throws ServletException,IOException {
        response.setHeader("Cache-Control","no-store");response.setHeader("Vary","Cookie");
        try{
            String path=request.getRequestURI(),method=request.getMethod();
            boolean read=method.equals("GET")||method.equals("HEAD");
            boolean bootstrap=path.equals("/api/v1/demo/session")||path.equals("/api/v1/demo/scenarios");
            var run=RUN.matcher(path);
            if(path.contains("%")||path.contains(".")||path.contains(";")||path.contains("//")||!(bootstrap||path.equals("/api/v1/demo/runs")||run.matches()))
                throw new DemoPublicAccess.Rejection(404,"NOT_FOUND","This demo endpoint is unavailable.",0);
            if(!read&&!method.equals("POST"))throw new DemoPublicAccess.Rejection(405,"METHOD_NOT_ALLOWED","This method is unavailable.",0);
            String credential=null;int cookieCount=0;
            if(request.getCookies()!=null)for(Cookie cookie:request.getCookies())if(cookie.getName().equals(access.cookieName())){credential=cookie.getValue();cookieCount++;}
            DemoPublicAccess.Session session=cookieCount>1?null:access.authenticate(credential);
            if(session==null&&bootstrap&&read){
                session=access.issue();response.addHeader("Set-Cookie",ResponseCookie.from(access.cookieName(),session.token()).httpOnly(true).secure(access.secure())
                        .sameSite("Strict").path("/").maxAge(DemoPublicAccess.SESSION_SECONDS).build().toString());
            }
            if(session==null)throw new DemoPublicAccess.Rejection(401,"SESSION_REQUIRED","Your visitor session is missing or expired. Reload the demo to start a new session.",0);
            access.request(session,method,path);
            if(!read&&(!sameOrigin(request)||!access.validCsrf(session,request.getHeader("X-Demo-CSRF"))))
                throw new DemoPublicAccess.Rejection(403,"CSRF_INVALID","The visitor session could not authorize this request. Reload the demo before trying again.",0);
            if(run.matches())access.requireOwner(session,run.group(1));
            request.setAttribute(DemoPublicAccess.REQUEST_SESSION,session);
            chain.doFilter(request,response);
        }catch(DemoPublicAccess.Rejection rejected){error(response,rejected.status,rejected.code,rejected.getMessage(),rejected.retryAfter);}
        catch(DataAccessException unavailable){error(response,503,"DEMO_UNAVAILABLE","The demo evidence store is unavailable. No success has been recorded.",10);}
    }
    private boolean sameOrigin(HttpServletRequest request){
        String value=request.getHeader("Origin");if(value==null||value.length()>512)return false;
        try{
            URI origin=URI.create(value);String authority=request.getHeader("Host");
            if(authority==null||authority.length()>255||!("https".equals(origin.getScheme())||"http".equals(origin.getScheme())))return false;
            // The gateway preserves the browser Host (including an explicit
            // port). Its internal HTTP hop cannot identify the outer scheme.
            URI requested=URI.create(origin.getScheme()+"://"+authority);
            int originPort=origin.getPort()<0?(origin.getScheme().equals("https")?443:80):origin.getPort();
            int requestPort=requested.getPort()<0?(origin.getScheme().equals("https")?443:80):requested.getPort();
            return origin.getRawUserInfo()==null&&origin.getRawQuery()==null&&origin.getRawFragment()==null
                    &&(origin.getRawPath()==null||origin.getRawPath().isEmpty())&&origin.getHost()!=null
                    &&requested.getRawUserInfo()==null&&requested.getHost()!=null
                    &&origin.getHost().equalsIgnoreCase(requested.getHost())&&originPort==requestPort;
        }
        catch(IllegalArgumentException malformed){return false;}
    }
    private void error(HttpServletResponse response,int status,String code,String message,int retry)throws IOException {
        response.setStatus(status);response.setContentType("application/json");
        Map<String,Object> body=new LinkedHashMap<>();body.put("code",code);body.put("message",message);
        if(retry>0){response.setHeader("Retry-After",Integer.toString(retry));body.put("retry_after_seconds",retry);}
        mapper.writeValue(response.getOutputStream(),body);
    }
}
