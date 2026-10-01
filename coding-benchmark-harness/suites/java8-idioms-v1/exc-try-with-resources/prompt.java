import java.io.IOException;
import java.io.Reader;

public class Solution {

    /**
     * A Reader that records whether it was closed. DO NOT MODIFY.
     */
    public static class CountingReader extends Reader {
        private final Reader delegate;
        private int closeCount = 0;

        public CountingReader(Reader delegate) {
            this.delegate = delegate;
        }

        /** How many times close() has been called. */
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

    /**
     * Counts the non-blank lines a Reader produces.
     *
     * A line is blank when it is empty or contains only whitespace. Lines are separated by "\n",
     * "\r\n" or "\r". The reader is always closed before this method returns, including when
     * reading fails, which must be achieved with try-with-resources rather than a finally block
     * that swallows exceptions.
     *
     * A null reader returns 0 and does nothing else.
     *
     * Example: a reader over "a\n\nb\n" returns 2.
     *
     * @param reader the source to read, may be null
     * @return the number of non-blank lines
     * @throws IOException if reading fails; the reader is still closed
     */
    public static int countNonBlankLines(Reader reader) throws IOException {
        throw new UnsupportedOperationException("TODO");
    }
}
