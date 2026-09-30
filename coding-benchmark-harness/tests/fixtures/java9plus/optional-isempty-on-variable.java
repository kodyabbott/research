import java.util.*;
public class Main {
    public static void main(String[] args) {
        Optional<String> maybe = Optional.of("x");
        System.out.println(maybe.isEmpty());
    }
}
