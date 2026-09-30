import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        System.out.println("a\nb".lines().collect(Collectors.toList()));
    }
}
