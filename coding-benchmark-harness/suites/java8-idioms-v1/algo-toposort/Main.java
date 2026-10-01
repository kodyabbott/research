import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Main {
    private static Map<String, List<String>> graph(Object... pairs) {
        Map<String, List<String>> out = new LinkedHashMap<String, List<String>>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put((String) pairs[i], (List<String>) pairs[i + 1]);
        }
        return out;
    }

    private static List<String> to(String... names) {
        return Arrays.asList(names);
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqList(to("a", "b"), Solution.topoSort(graph("a", to("b"), "b", to())),
                "javadoc-example");

        // 2-3: empty and null graphs.
        Check.eqList(new ArrayList<String>(),
                Solution.topoSort(new LinkedHashMap<String, List<String>>()), "empty-graph");
        Check.eqList(new ArrayList<String>(), Solution.topoSort(null), "null-graph");

        // 4: alphabetical tie-break among independent nodes (not shown in the Javadoc).
        Check.eqList(to("a", "b", "c"),
                Solution.topoSort(graph("c", to(), "a", to(), "b", to())), "alphabetical-ties");

        // 5: a node that appears only inside a value list is still in the result.
        Check.eqList(to("a", "b"), Solution.topoSort(graph("a", to("b"))), "implicit-node");

        // 6: dependency order beats alphabetical order.
        Check.eqList(to("z", "a"), Solution.topoSort(graph("z", to("a"))),
                "dependency-beats-alphabet");

        // 7: a diamond, with ties broken alphabetically at each step.
        Check.eqList(to("a", "b", "c", "d"), Solution.topoSort(
                graph("a", to("b", "c"), "b", to("d"), "c", to("d"))), "diamond");

        // 8: isolated nodes mix with connected ones. Once "a" is emitted, "b" has no remaining
        // dependencies, so it joins the ready set and sorts before "m" -- the ready set is not
        // drained before newly freed nodes are considered.
        Check.eqList(to("a", "b", "m", "z"), Solution.topoSort(
                graph("a", to("b"), "m", to(), "z", to())), "isolated-nodes");

        // 9: a null value list means no outgoing edges.
        Check.eqList(to("a"), Solution.topoSort(graph("a", null)), "null-value-list");

        // 10: duplicate edges are ignored.
        Check.eqList(to("a", "b"), Solution.topoSort(graph("a", to("b", "b", "b"))),
                "duplicate-edges");

        // 11: a longer chain.
        Check.eqList(to("a", "b", "c", "d"), Solution.topoSort(
                graph("a", to("b"), "b", to("c"), "c", to("d"))), "chain");

        // 12-14: cycles. The contract fixes the type and that the message names a node in the
        // cycle, never the exact wording.
        Check.throwsTypeMentioning(IllegalArgumentException.class, new String[] {"a", "b"},
                () -> Solution.topoSort(graph("a", to("b"), "b", to("a"))), "two-cycle");
        Check.throwsTypeMentioning(IllegalArgumentException.class, new String[] {"x"},
                () -> Solution.topoSort(graph("x", to("x"))), "self-cycle");
        Check.throwsTypeMentioning(IllegalArgumentException.class, new String[] {"p", "q", "r"},
                () -> Solution.topoSort(graph("p", to("q"), "q", to("r"), "r", to("p"))),
                "three-cycle");

        // 15: a cycle plus a valid tail still throws.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.topoSort(graph("a", to("b"), "b", to("a"), "ok", to())),
                "cycle-with-acyclic-part");

        Check.report();
    }
}
