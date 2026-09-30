import java.util.*;
public class Main {
    public static void main(String[] args) {
        Comparator<String> c = new Comparator<>() {
            public int compare(String a, String b) { return a.compareTo(b); }
        };
        System.out.println(c.compare("a", "b"));
    }
}
