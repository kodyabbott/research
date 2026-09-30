public class Main {
    interface Greeter {
        private String hidden() { return "hi"; }
        default String greet() { return hidden(); }
    }
    public static void main(String[] args) {
        System.out.println(((Greeter) new Greeter() {}).greet());
    }
}
