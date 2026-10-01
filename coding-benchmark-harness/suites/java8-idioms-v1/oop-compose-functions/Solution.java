import java.util.List;
import java.util.function.Function;

public class Solution {

    public static Function<String, String> composeAll(List<Function<String, String>> functions) {
        Function<String, String> composed = Function.identity();
        if (functions == null) {
            return composed;
        }
        for (Function<String, String> next : functions) {
            if (next == null) {
                continue;
            }
            composed = composed.andThen(next);
        }
        return composed;
    }
}
