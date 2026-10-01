import java.util.List;

public class Solution {

    /**
     * Parses one RFC 4180 CSV record into its fields.
     *
     * Fields are separated by commas. A field may be wrapped in double quotes, in which case a
     * comma inside it is literal and a doubled quote ("") means one literal quote character.
     * Quotes are only special at the start of a field. Whitespace is never trimmed. An empty input
     * yields a single empty field. A trailing comma yields a trailing empty field.
     *
     * Example: a,"b,c","d""e" returns ["a", "b,c", "d\"e"].
     *
     * @param line one CSV record, without its line terminator
     * @return the fields in order
     * @throws IllegalArgumentException if line is null, or a quoted field is never closed, or a
     *                                  closing quote is followed by anything but a comma or the
     *                                  end of the line
     */
    public static List<String> parseLine(String line) {
        throw new UnsupportedOperationException("TODO");
    }
}
