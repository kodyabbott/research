public class Main {
    public static void main(String[] args) {
        Object o = "text";
        if (o instanceof String s && s.length() > 2) {
            System.out.println(s);
        }
    }
}
