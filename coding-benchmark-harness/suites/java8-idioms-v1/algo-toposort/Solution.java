import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.TreeSet;

public class Solution {

    public static List<String> topoSort(Map<String, List<String>> graph) {
        Map<String, Set<String>> edges = new HashMap<String, Set<String>>();
        Set<String> nodes = new TreeSet<String>();
        if (graph != null) {
            for (Map.Entry<String, List<String>> entry : graph.entrySet()) {
                nodes.add(entry.getKey());
                Set<String> targets = edges.get(entry.getKey());
                if (targets == null) {
                    targets = new LinkedHashSet<String>();
                    edges.put(entry.getKey(), targets);
                }
                if (entry.getValue() == null) {
                    continue;
                }
                for (String target : entry.getValue()) {
                    if (target == null) {
                        continue;
                    }
                    nodes.add(target);
                    targets.add(target);
                }
            }
        }
        Map<String, Integer> inDegree = new HashMap<String, Integer>();
        for (String node : nodes) {
            inDegree.put(node, 0);
        }
        for (Map.Entry<String, Set<String>> entry : edges.entrySet()) {
            for (String target : entry.getValue()) {
                inDegree.put(target, inDegree.get(target) + 1);
            }
        }
        PriorityQueue<String> ready = new PriorityQueue<String>();
        for (String node : nodes) {
            if (inDegree.get(node) == 0) {
                ready.add(node);
            }
        }
        List<String> order = new ArrayList<String>();
        while (!ready.isEmpty()) {
            String node = ready.poll();
            order.add(node);
            Set<String> targets = edges.get(node);
            if (targets == null) {
                continue;
            }
            for (String target : targets) {
                int remaining = inDegree.get(target) - 1;
                inDegree.put(target, remaining);
                if (remaining == 0) {
                    ready.add(target);
                }
            }
        }
        if (order.size() != nodes.size()) {
            Set<String> stuck = new TreeSet<String>(nodes);
            stuck.removeAll(new HashSet<String>(order));
            throw new IllegalArgumentException("cycle detected involving: " + stuck);
        }
        return order;
    }
}
