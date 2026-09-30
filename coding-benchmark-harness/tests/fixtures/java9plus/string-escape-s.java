public class Main {
    public static void main(String[] args) {
        String[] parts = "a b".split("[.?!]\s*");
        System.out.println(parts.length);
    }
}
