import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Solution {

    /**
     * Thrown when a form fails validation. DO NOT MODIFY.
     */
    public static class ValidationException extends Exception {
        private static final long serialVersionUID = 1L;
        private final List<String> errors;

        public ValidationException(List<String> errors) {
            super("validation failed with " + errors.size() + " error(s)");
            this.errors = errors;
        }

        /** All validation messages, in field-name order. */
        public List<String> getErrors() {
            return errors;
        }
    }

    /**
     * Validates a form and returns its normalized values.
     *
     * Rules, applied to every required field rather than stopping at the first failure:
     *   a required field that is absent produces "<field> is required"
     *   a required field whose value is null or blank once trimmed produces "<field> is blank"
     * Messages are collected for every field, sorted by field name ascending, and thrown together
     * in one ValidationException. Fields not in required are left alone.
     *
     * When there are no errors, the returned map contains every entry of form with its value
     * trimmed, ordered by key ascending.
     *
     * A null form is treated as empty. A null required list means nothing is required.
     *
     * Example: form {name=" ann "} with required ["name"] returns {name=ann}.
     *
     * @param form     the submitted values, may be null
     * @param required the field names that must be present and non-blank, may be null
     * @return the trimmed values, ordered by key
     * @throws ValidationException if any required field is missing or blank
     */
    public static TreeMap<String, String> validate(Map<String, String> form, List<String> required)
            throws ValidationException {
        throw new UnsupportedOperationException("TODO");
    }
}
