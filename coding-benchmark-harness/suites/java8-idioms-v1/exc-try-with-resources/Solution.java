import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;

public class Solution {

    public static class CountingReader extends Reader {
        private final Reader delegate;
        private int closeCount = 0;

        public CountingReader(Reader delegate) {
            this.delegate = delegate;
        }

        public int closeCount() {
            return closeCount;
        }

        @Override
        public int read(char[] buffer, int offset, int length) throws IOException {
            return delegate.read(buffer, offset, length);
        }

        @Override
        public void close() throws IOException {
            closeCount++;
            delegate.close();
        }
    }

    public static int countNonBlankLines(Reader reader) throws IOException {
        if (reader == null) {
            return 0;
        }
        int count = 0;
        try (BufferedReader lines = new BufferedReader(reader)) {
            String line;
            while ((line = lines.readLine()) != null) {
                if (!line.trim().isEmpty()) {
                    count++;
                }
            }
        }
        return count;
    }
}
