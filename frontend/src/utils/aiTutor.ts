/**
 * CAMS AI Tutor Utilities.
 * Pure functions for cleaning and formatting AI responses.
 */

// Matches full <board>...</board> tags (including attributes if any, case-insensitive, multiline)
const FULL_BOARD_TAG_REGEX = /<board(?:\s+[^>]*)?>[\s\S]*?<\/board>/gi;

// Matches an unclosed <board tag up to the end of the string (during streaming)
const UNCLOSED_BOARD_TAG_REGEX = /<board[\s\S]*$/i;

// Matches incomplete opening tag prefixes at the very end of string (e.g. "<", "<b", "<bo", "<boa", "<boar")
const INCOMPLETE_TAG_PREFIX_REGEX = /<b(?:o(?:a(?:r(?:d)?)?)?)?$/i;

/**
 * Strips <board>...</board> blocks from AI message text.
 * - Handles multiline, non-greedy match across newlines and whitespace.
 * - In streaming mode, hides partially emitted <board tags so text/JSON does not flash on screen.
 * - Collapses 3+ consecutive newlines into 2, and trims whitespace.
 *
 * @param text The raw message content from AI
 * @param isStreaming Whether the message is actively receiving chunks
 * @returns Cleaned text suitable for chat bubble display
 */
export function stripBoardTags(text: string, isStreaming: boolean = false): string {
  if (!text) return '';

  // 1. Remove all fully closed <board>...</board> tags
  let cleaned = text.replace(FULL_BOARD_TAG_REGEX, '');

  // 2. If actively streaming, suppress incomplete tags and their contents
  if (isStreaming) {
    // If an unclosed <board tag exists, strip from <board onwards
    cleaned = cleaned.replace(UNCLOSED_BOARD_TAG_REGEX, '');

    // If an opening tag prefix is forming at the end (e.g. "<boa"), strip it
    cleaned = cleaned.replace(INCOMPLETE_TAG_PREFIX_REGEX, '');
  }

  // 3. Normalize excess newlines left behind after tag removal
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
}
