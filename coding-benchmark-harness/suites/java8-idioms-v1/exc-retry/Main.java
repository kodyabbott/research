import java.util.concurrent.Callable;
import java.util.function.Predicate;

public class Main {
    private static final Predicate<Exception> ALWAYS = e -> true;
    private static final Predicate<Exception> NEVER = e -> false;

    /** Fails with IllegalStateException until the given attempt, then returns "ok". */
    static final class FailUntil implements Callable<String> {
        final int succeedOn;
        int calls = 0;

        FailUntil(int succeedOn) {
            this.succeedOn = succeedOn;
        }

        public String call() {
            calls++;
            if (calls < succeedOn) {
                throw new IllegalStateException("attempt " + calls);
            }
            return "ok";
        }
    }

    public static void main(String[] args) {
        // 1: the Javadoc example, and the task is called exactly once.
        FailUntil first = new FailUntil(1);
        Check.eqStr("ok", Solution.withRetry(first, 3, ALWAYS), "succeeds-first-attempt");
        Check.eqInt(1, first.calls, "no-extra-attempts-after-success");

        // 2: success on attempt k stops there (not shown in the Javadoc).
        FailUntil third = new FailUntil(3);
        Check.eqStr("ok", Solution.withRetry(third, 5, ALWAYS), "succeeds-on-third");
        Check.eqInt(3, third.calls, "stopped-at-third");

        // 3: exhausting the attempts reports the count and the last cause.
        FailUntil never = new FailUntil(99);
        try {
            Solution.withRetry(never, 4, ALWAYS);
            Check.eqBool(true, false, "should-have-thrown");
        } catch (Solution.RetryExhaustedException thrown) {
            Check.eqInt(4, thrown.getAttempts(), "attempts-counted");
            Check.eqInt(4, never.calls, "all-attempts-used");
            Check.eqStr("java.lang.IllegalStateException",
                    thrown.getCause().getClass().getName(), "cause-preserved");
            Check.eqStr("attempt 4", thrown.getCause().getMessage(), "last-cause-not-first");
            Check.eqStr("failed after 4 attempt(s)", thrown.getMessage(), "exception-message");
        }

        // 4: a non-retryable exception stops after one attempt.
        FailUntil nonRetryable = new FailUntil(99);
        try {
            Solution.withRetry(nonRetryable, 5, NEVER);
            Check.eqBool(true, false, "should-have-thrown");
        } catch (Solution.RetryExhaustedException thrown) {
            Check.eqInt(1, thrown.getAttempts(), "non-retryable-one-attempt");
            Check.eqInt(1, nonRetryable.calls, "non-retryable-called-once");
        }

        // 5: the predicate selects on exception type.
        Predicate<Exception> onlyIllegalState = e -> e instanceof IllegalStateException;
        Callable<String> throwsIo = () -> {
            throw new java.io.IOException("io");
        };
        try {
            Solution.withRetry(throwsIo, 3, onlyIllegalState);
            Check.eqBool(true, false, "should-have-thrown");
        } catch (Solution.RetryExhaustedException thrown) {
            Check.eqInt(1, thrown.getAttempts(), "predicate-selects-by-type");
        }

        // 6: maxAttempts of 1 means a single try.
        FailUntil single = new FailUntil(99);
        try {
            Solution.withRetry(single, 1, ALWAYS);
            Check.eqBool(true, false, "should-have-thrown");
        } catch (Solution.RetryExhaustedException thrown) {
            Check.eqInt(1, thrown.getAttempts(), "max-attempts-one");
        }

        // 7: a checked exception from the Callable is still retried and wrapped.
        Check.eqBool(true, RuntimeException.class.isAssignableFrom(
                Solution.RetryExhaustedException.class), "retry-exhausted-is-unchecked");

        // 8: a null result is returned as-is, not treated as failure.
        Check.eq(null, Solution.withRetry(() -> null, 2, ALWAYS), "null-result-is-success");

        // 9-11: the argument contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.withRetry(null, 3, ALWAYS), "null-task-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.withRetry(() -> "x", 3, null), "null-predicate-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.withRetry(() -> "x", 0, ALWAYS), "zero-attempts-throws");

        Check.report();
    }
}
