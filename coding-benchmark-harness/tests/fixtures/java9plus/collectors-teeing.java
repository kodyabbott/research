import java.util.*;
import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        Object r = Stream.of(1, 2).collect(Collectors.teeing(
                Collectors.counting(), Collectors.counting(), (a, b) -> a));
        System.out.println(r);
    }
}
