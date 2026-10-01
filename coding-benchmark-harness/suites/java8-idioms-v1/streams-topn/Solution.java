import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class Solution {

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

    public static List<String> topN(List<Player> players, int n) {
        if (players == null || n <= 0) {
            return new ArrayList<String>();
        }
        return players.stream()
                .filter(p -> p != null)
                .sorted(Comparator.comparingInt(Player::score).reversed()
                        .thenComparing(Player::name))
                .limit(n)
                .map(Player::name)
                .collect(Collectors.toList());
    }
}
