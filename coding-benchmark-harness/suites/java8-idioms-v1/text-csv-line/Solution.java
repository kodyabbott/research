import java.util.ArrayList;
import java.util.List;

public class Solution {

    public static List<String> parseLine(String line) {
        if (line == null) {
            throw new IllegalArgumentException("line must not be null");
        }
        List<String> fields = new ArrayList<String>();
        StringBuilder field = new StringBuilder();
        int index = 0;
        while (index <= line.length()) {
            if (index == line.length()) {
                fields.add(field.toString());
                break;
            }
            char c = line.charAt(index);
            if (field.length() == 0 && c == '"') {
                index++;
                boolean closed = false;
                while (index < line.length()) {
                    char inner = line.charAt(index);
                    if (inner == '"') {
                        if (index + 1 < line.length() && line.charAt(index + 1) == '"') {
                            field.append('"');
                            index += 2;
                            continue;
                        }
                        index++;
                        closed = true;
                        break;
                    }
                    field.append(inner);
                    index++;
                }
                if (!closed) {
                    throw new IllegalArgumentException("unterminated quoted field: " + line);
                }
                if (index < line.length() && line.charAt(index) != ',') {
                    throw new IllegalArgumentException("text after a closing quote: " + line);
                }
                if (index == line.length()) {
                    fields.add(field.toString());
                    break;
                }
                fields.add(field.toString());
                field.setLength(0);
                index++;
                if (index == line.length()) {
                    fields.add("");
                    break;
                }
                continue;
            }
            if (c == ',') {
                fields.add(field.toString());
                field.setLength(0);
                index++;
                if (index == line.length()) {
                    fields.add("");
                    break;
                }
                continue;
            }
            field.append(c);
            index++;
        }
        return fields;
    }
}
