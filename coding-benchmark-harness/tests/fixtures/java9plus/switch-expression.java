public class Main {
    public static void main(String[] args) {
        int day = 3;
        String name = switch (day) {
            case 1 -> "Mon";
            default -> "other";
        };
        System.out.println(name);
    }
}
