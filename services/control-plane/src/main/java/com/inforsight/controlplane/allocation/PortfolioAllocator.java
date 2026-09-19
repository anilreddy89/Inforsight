package com.inforsight.controlplane.allocation;

import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PortfolioAllocator {
    public Allocation allocate(List<Candidate> candidates, long budgetMicros, int personnelSeconds) {
        if (budgetMicros < 0 || personnelSeconds < 0) throw new IllegalArgumentException("capacities must be nonnegative");
        List<Candidate> ordered = candidates.stream()
                .filter(Candidate::eligible)
                .sorted(Comparator.comparing(Candidate::policyId).thenComparing(Candidate::actionType))
                .toList();
        Map<Capacity, State> states = new HashMap<>();
        states.put(new Capacity(0, 0), new State(0, List.of()));
        for (Candidate candidate : ordered) {
            Map<Capacity, State> next = new HashMap<>(states);
            for (Map.Entry<Capacity, State> entry : states.entrySet()) {
                Capacity current = entry.getKey();
                long money = current.money() + candidate.costMicros();
                int time = current.time() + candidate.personnelSeconds();
                if (money > budgetMicros || time > personnelSeconds) continue;
                State alternative = new State(entry.getValue().objective() + candidate.netUtilityMicros(), append(entry.getValue().selected(), candidate));
                Capacity capacity = new Capacity(money, time);
                State incumbent = next.get(capacity);
                if (incumbent == null || better(alternative, incumbent)) next.put(capacity, alternative);
            }
            states = next;
        }
        Map.Entry<Capacity, State> best = states.entrySet().stream().max((left, right) -> {
            int objective = Long.compare(left.getValue().objective(), right.getValue().objective());
            if (objective != 0) return objective;
            return right.getValue().signature().compareTo(left.getValue().signature());
        }).orElseThrow();
        return new Allocation(best.getValue().selected(), best.getKey().money(), best.getKey().time(), best.getValue().objective());
    }

    private static List<Candidate> append(List<Candidate> current, Candidate candidate) {
        java.util.ArrayList<Candidate> result = new java.util.ArrayList<>(current);
        result.add(candidate);
        return List.copyOf(result);
    }

    private static boolean better(State alternative, State incumbent) {
        return alternative.objective() > incumbent.objective()
                || (alternative.objective() == incumbent.objective() && alternative.signature().compareTo(incumbent.signature()) < 0);
    }

    public record Candidate(String policyId, String actionType, long costMicros, int personnelSeconds, long netUtilityMicros, boolean eligible) {}
    public record Allocation(List<Candidate> selected, long usedMoneyMicros, int usedPersonnelSeconds, long objectiveMicros) {}
    private record Capacity(long money, int time) {}
    private record State(long objective, List<Candidate> selected) {
        String signature() { return selected.stream().map(c -> c.policyId() + ":" + c.actionType()).sorted().reduce("", (a, b) -> a + "|" + b); }
    }
}
