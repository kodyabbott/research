import java.util.List;
import java.util.Map;

public class Solution {

    /**
     * Topologically sorts a dependency graph, breaking ties alphabetically.
     *
     * The map goes from a node to the nodes that depend on it, so an edge a -> b means a must come
     * before b. Every node named anywhere, whether as a key or only inside a value list, is part of
     * the graph and appears in the result exactly once. Nodes with no remaining dependencies are
     * emitted in ascending alphabetical order, which makes the output deterministic. A node whose
     * value list is empty or null has no outgoing edges. A null graph is treated as empty.
     * Duplicate edges are ignored.
     *
     * Example: {a=[b], b=[]} returns ["a", "b"].
     *
     * @param graph node to its dependents, may be null
     * @return every node in a valid topological order, ties alphabetical
     * @throws IllegalArgumentException if the graph contains a cycle; the message names at least
     *                                  one node that is part of a cycle
     */
    public static List<String> topoSort(Map<String, List<String>> graph) {
        throw new UnsupportedOperationException("TODO");
    }
}
