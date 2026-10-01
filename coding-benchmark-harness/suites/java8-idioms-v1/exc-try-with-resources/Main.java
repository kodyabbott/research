import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

public class Main {
    /** Always fails on read, so the close-on-failure path can be observed. */
    static final class FailingReader extends Reader {
        int closeCount = 0;

        public int read(char[] buffer, int offset, int length) throws IOException {
            throw new IOException("read failed");
        }

        public void close() {
            closeCount++;
        }
    }

    public static void main(String[] args) throws Exception {
        // 1: the Javadoc example.
        Check.eqInt(2, Solution.countNonBlankLines(new StringReader("a\n\nb\n")),
                "javadoc-example");

        // 2: null reader.
        Check.eqInt(0, Solution.countNonBlankLines(null), "null-reader");

        // 3-4: empty and whitespace-only input (not shown in the Javadoc).
        Check.eqInt(0, Solution.countNonBlankLines(new StringReader("")), "empty-input");
        Check.eqInt(0, Solution.countNonBlankLines(new StringReader("   \n\t\n  ")),
                "whitespace-only");

        // 5: no trailing newline still counts the last line.
        Check.eqInt(1, Solution.countNonBlankLines(new StringReader("last")), "no-trailing-newline");

        // 6-7: CRLF and bare CR separators.
        Check.eqInt(2, Solution.countNonBlankLines(new StringReader("a\r\n\r\nb")), "crlf");
        Check.eqInt(2, Solution.countNonBlankLines(new StringReader("a\r\rb")), "bare-cr");

        // 8: the reader is closed exactly once on the success path.
        Solution.CountingReader ok = new Solution.CountingReader(new StringReader("x\ny\n"));
        Check.eqInt(2, Solution.countNonBlankLines(ok), "counts-with-counting-reader");
        Check.eqInt(1, ok.closeCount(), "closed-once-on-success");

        // 9: the reader is closed even when reading throws, and the IOException propagates.
        final FailingReader failing = new FailingReader();
        Check.throwsType(IOException.class, () -> Solution.countNonBlankLines(failing),
                "ioexception-propagates");
        Check.eqInt(1, failing.closeCount, "closed-once-on-failure");

        // 10: lines with surrounding spaces count as non-blank.
        Check.eqInt(1, Solution.countNonBlankLines(new StringReader("  a  \n   \n")),
                "padded-line-counts");

        // 11: many lines.
        Check.eqInt(3, Solution.countNonBlankLines(new StringReader("1\n\n2\n\n\n3")),
                "several-blank-runs");

        Check.report();
    }
}
