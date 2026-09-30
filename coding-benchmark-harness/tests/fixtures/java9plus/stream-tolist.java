import java.util.*;
import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        List<String> xs = Stream.of("a", "b").toList();
        System.out.println(xs);
    }
}
