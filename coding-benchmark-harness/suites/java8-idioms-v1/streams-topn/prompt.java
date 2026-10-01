import java.util.List;

public class Solution {

    /**
     * A scored player. DO NOT MODIFY this nested class.
     */
    public static final class Player {
        private final String name;
        private final int score;

        public Player(String name, int score) {
            this.name = name;
            this.score = score;
        }

        public String name() {
            return name;
        }

        public int score() {
            return score;
        }
    }

    /**
     * Returns the names of the top n players, ordered by score descending and then by name
     * ascending for equal scores.
     *
     * If n is greater than the number of players, every player is returned. If n is zero or
     * negative, an empty list is returned. A null players list is treated as empty. Null elements
     * are ignored.
     *
     * Example: [("ann", 5), ("bob", 9)] with n = 1 returns ["bob"].
     *
     * @param players the players to rank, may be null or contain nulls
     * @param n       how many names to return
     * @return the top n names, highest score first
     */
    public static List<String> topN(List<Player> players, int n) {
        throw new UnsupportedOperationException("TODO");
    }
}
