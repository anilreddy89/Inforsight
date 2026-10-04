package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.Set;
import static org.assertj.core.api.Assertions.*;

class DemoInputContractTest {
    @Test void forbidsAuthorityAndExternalConnectorFields() throws Exception {
        var mapper=new ObjectMapper();
        for(String field:Set.of("authorized_to_act","webhook_url","selected_action","case_version")){
            var body=mapper.createObjectNode().put("scenario_id","late-payment").put(field,true);
            assertThatThrownBy(()->DemoJourneyController.exact(body,Set.of("scenario_id","overrides")))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("unsupported field");
        }
        assertThatThrownBy(()->DemoJourneyController.exact(mapper.createArrayNode(),Set.of("scenario_id"))).isInstanceOf(IllegalArgumentException.class);
    }
}
