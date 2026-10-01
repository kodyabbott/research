import java.util.concurrent.Callable;
import java.util.function.Predicate;

public class Solution {

    public static class RetryExhaustedException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        private final int attempts;

        public RetryExhaustedException(int attempts, Throwable cause) {
            super("failed after " + attempts + " attempt(s)", cause);
            this.attempts = attempts;
        }

        public int getAttempts() {
            return attempts;
        }
    }

    public static <T> T withRetry(Callable<T> task, int maxAttempts,
                                  Predicate<Exception> retryable) {
        if (task == null || retryable == null) {
            throw new IllegalArgumentException("task and retryable must not be null");
        }
        if (maxAttempts < 1) {
            throw new IllegalArgumentException("maxAttempts must be at least 1");
        }
        int attempts = 0;
        Exception last = null;
        while (attempts < maxAttempts) {
            attempts++;
            try {
                return task.call();
            } catch (Exception thrown) {
                last = thrown;
                if (!retryable.test(thrown)) {
                    break;
                }
            }
        }
        throw new RetryExhaustedException(attempts, last);
    }
}
