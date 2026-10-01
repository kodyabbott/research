import java.util.concurrent.Callable;
import java.util.function.Predicate;

public class Solution {

    /**
     * Thrown when every retry attempt failed. DO NOT MODIFY.
     */
    public static class RetryExhaustedException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        private final int attempts;

        public RetryExhaustedException(int attempts, Throwable cause) {
            super("failed after " + attempts + " attempt(s)", cause);
            this.attempts = attempts;
        }

        /** How many attempts were made. */
        public int getAttempts() {
            return attempts;
        }
    }

    /**
     * Calls a task, retrying only for exceptions the predicate accepts.
     *
     * The task is attempted up to maxAttempts times. After a failure, if the predicate rejects the
     * exception, or no attempts remain, a RetryExhaustedException is thrown whose cause is that
     * last exception and whose getAttempts() is the number of attempts actually made. A successful
     * attempt returns its value immediately and makes no further attempt.
     *
     * Example: a task that succeeds on its first call returns that value after one attempt.
     *
     * @param task        the work to attempt; never null
     * @param maxAttempts how many times to try; at least 1
     * @param retryable   decides whether an exception is worth retrying; never null
     * @param <T>         the result type
     * @return the task's value
     * @throws IllegalArgumentException   if task or retryable is null, or maxAttempts is below 1
     * @throws RetryExhaustedException    if no attempt succeeded
     */
    public static <T> T withRetry(Callable<T> task, int maxAttempts,
                                  Predicate<Exception> retryable) {
        throw new UnsupportedOperationException("TODO");
    }
}
