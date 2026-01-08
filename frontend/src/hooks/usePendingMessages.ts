/**
 * Hook for polling pending chat messages.
 *
 * This hook monitors messages that are being generated in the background
 * and updates them when complete.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { getMessageStatus, ChatMessage, MessageStatusResponse } from "../lib/apiClient";

interface UsePendingMessagesOptions {
  // Messages to monitor
  messages: ChatMessage[];
  // Callback when a message is updated
  onMessageUpdate: (messageId: string, updates: Partial<ChatMessage>) => void;
  // Polling interval in milliseconds (default: 2000)
  pollingInterval?: number;
  // Whether polling is enabled
  enabled?: boolean;
}

interface UsePendingMessagesReturn {
  // IDs of messages currently being polled
  pendingIds: string[];
  // Whether any messages are pending
  hasPending: boolean;
  // Manually trigger a status check
  checkStatus: (messageId: string) => Promise<void>;
}

export function usePendingMessages({
  messages,
  onMessageUpdate,
  pollingInterval = 2000,
  enabled = true,
}: UsePendingMessagesOptions): UsePendingMessagesReturn {
  const [pendingIds, setPendingIds] = useState<string[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Find pending/generating messages (only those with valid IDs)
  const findPendingMessages = useCallback(() => {
    return messages.filter(
      (msg) =>
        msg.id && // Ensure message has a valid ID
        msg.role === "assistant" &&
        (msg.status === "pending" || msg.status === "generating")
    );
  }, [messages]);

  // Check status of a single message
  const checkStatus = useCallback(
    async (messageId: string) => {
      if (!messageId) {
        console.warn("checkStatus called with empty messageId");
        return;
      }
      try {
        const status: MessageStatusResponse = await getMessageStatus(messageId);

        if (status.status === "completed" || status.status === "failed") {
          onMessageUpdate(messageId, {
            status: status.status,
            content: status.content || "",
            source_refs: status.source_refs || null,
            error_message: status.error_message,
          });
        } else if (status.status === "generating") {
          // Update status to generating if it was pending
          onMessageUpdate(messageId, { status: "generating" });
        }
      } catch (error) {
        console.error(`Failed to check message status: ${messageId}`, error);
      }
    },
    [onMessageUpdate]
  );

  // Poll pending messages
  const pollPendingMessages = useCallback(async () => {
    const pending = findPendingMessages();
    setPendingIds(pending.map((m) => m.id));

    if (pending.length === 0) {
      return;
    }

    // Check all pending messages in parallel
    await Promise.all(pending.map((msg) => checkStatus(msg.id)));
  }, [findPendingMessages, checkStatus]);

  // Set up polling interval
  useEffect(() => {
    if (!enabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Initial check
    pollPendingMessages();

    // Set up interval
    intervalRef.current = setInterval(pollPendingMessages, pollingInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, pollingInterval, pollPendingMessages]);

  // Update pending IDs when messages change
  useEffect(() => {
    const pending = findPendingMessages();
    setPendingIds(pending.map((m) => m.id));
  }, [messages, findPendingMessages]);

  return {
    pendingIds,
    hasPending: pendingIds.length > 0,
    checkStatus,
  };
}
