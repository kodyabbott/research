import java.io.ByteArrayOutputStream;
import java.io.UnsupportedEncodingException;
import java.util.LinkedHashMap;

public class Solution {

    public static LinkedHashMap<String, String> parse(String input) {
        LinkedHashMap<String, String> out = new LinkedHashMap<String, String>();
        if (input == null || input.trim().isEmpty()) {
            return out;
        }
        String[] segments = input.split(";", -1);
        for (String segment : segments) {
            if (segment.isEmpty()) {
                continue;
            }
            int split = segment.indexOf('=');
            if (split < 0) {
                throw new IllegalArgumentException("segment has no '=': " + segment);
            }
            String key = decode(segment.substring(0, split));
            String value = decode(segment.substring(split + 1));
            if (key.isEmpty()) {
                throw new IllegalArgumentException("empty key in: " + segment);
            }
            out.put(key, value);
        }
        return out;
    }

    private static String decode(String text) {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        int index = 0;
        while (index < text.length()) {
            char c = text.charAt(index);
            if (c == '%') {
                if (index + 3 > text.length()) {
                    throw new IllegalArgumentException("truncated escape in: " + text);
                }
                String hex = text.substring(index + 1, index + 3);
                int high = Character.digit(hex.charAt(0), 16);
                int low = Character.digit(hex.charAt(1), 16);
                if (high < 0 || low < 0) {
                    throw new IllegalArgumentException("bad escape '%" + hex + "' in: " + text);
                }
                bytes.write(high * 16 + low);
                index += 3;
                continue;
            }
            byte[] encoded;
            try {
                encoded = String.valueOf(c).getBytes("UTF-8");
            } catch (UnsupportedEncodingException impossible) {
                throw new IllegalStateException(impossible);
            }
            bytes.write(encoded, 0, encoded.length);
            index++;
        }
        try {
            return new String(bytes.toByteArray(), "UTF-8");
        } catch (UnsupportedEncodingException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
