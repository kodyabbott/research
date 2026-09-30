import java.io.*;
public class Main {
    public static void main(String[] args) throws Exception {
        Reader r = new StringReader("x");
        try (r) {
            System.out.println(r.read());
        }
    }
}
