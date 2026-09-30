import java.util.*;
public class Main {
    public static void main(String[] args) {
        List<Integer> out = new ArrayList<>();
        String k = "o";
        switch (k) {
            case "o" -> out.add(4);
            case "p" -> out.add(2);
        }
        System.out.println(out);
    }
}
