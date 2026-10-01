import java.util.Optional;
import java.util.function.BinaryOperator;

public class Main {
    private static final BinaryOperator<Integer> ADD = (a, b) -> a + b;

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eq(Optional.of(5), Solution.merge(Optional.of(2), Optional.of(3), ADD),
                "javadoc-example");

        // 2-3: exactly one present is returned unchanged.
        Check.eq(Optional.of(2), Solution.merge(Optional.of(2), Optional.empty(), ADD),
                "left-only");
        Check.eq(Optional.of(3), Solution.merge(Optional.empty(), Optional.of(3), ADD),
                "right-only");

        // 4: neither present.
        Check.eq(Optional.empty(), Solution.merge(Optional.empty(), Optional.empty(), ADD),
                "neither");

        // 5-6: null Optional arguments behave as empty (not shown in the Javadoc example).
        Check.eq(Optional.of(4), Solution.merge(null, Optional.of(4), ADD), "null-left");
        Check.eq(Optional.of(1), Solution.merge(Optional.of(1), null, ADD), "null-right");
        Check.eq(Optional.empty(), Solution.merge(null, null, ADD), "both-null");

        // 7: argument order reaches the merger as (left, right).
        Check.eq(Optional.of(10), Solution.merge(Optional.of(13), Optional.of(3),
                (a, b) -> a - b), "argument-order-left-then-right");

        // 8: a merger returning null yields empty.
        Check.eq(Optional.empty(), Solution.merge(Optional.of(1), Optional.of(2),
                (a, b) -> null), "merger-returning-null");

        // 9: the one-present branch does not call the merger at all.
        Check.eq(Optional.of(6), Solution.merge(Optional.of(6), Optional.empty(),
                (a, b) -> { throw new IllegalStateException("must not be called"); }),
                "merger-not-called-when-one-present");

        // 10: the merger contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.merge(Optional.of(1), Optional.of(2), null),
                "null-merger-throws");

        Check.report();
    }
}
