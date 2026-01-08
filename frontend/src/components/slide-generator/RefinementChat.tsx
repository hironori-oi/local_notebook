"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Bot, User } from "lucide-react";
import { SlideMessage } from "../../lib/slideGeneratorApi";

interface RefinementChatProps {
  messages: SlideMessage[];
  onSend: (instruction: string) => void;
  loading?: boolean;
}

export function RefinementChat({ messages, onSend, loading = false }: RefinementChatProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    onSend(input.trim());
    setInput("");
  };

  const suggestedPrompts = [
    "全体的にもう少し簡潔にしてください",
    "具体例を追加してください",
    "スライドを1枚追加してください",
    "結論をより強調してください",
  ];

  return (
    <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft border border-surface-200 dark:border-surface-700 h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-surface-200 dark:border-surface-700">
        <h3 className="font-medium text-surface-900 dark:text-surface-100">
          修正指示
        </h3>
        <p className="text-sm text-surface-500 mt-1">
          チャット形式でスライドの修正を依頼できます
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px] max-h-[400px]">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <Bot className="w-12 h-12 mx-auto text-surface-300 mb-4" />
            <p className="text-surface-500 text-sm">
              スライドの修正指示を入力してください
            </p>
            <div className="mt-4 space-y-2">
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInput(prompt)}
                  className="block w-full text-left px-4 py-3 text-sm text-surface-600 dark:text-surface-300
                             bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700
                             rounded-xl hover:border-primary-300 dark:hover:border-primary-700
                             hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.role === "user" ? "flex-row-reverse" : ""
                }`}
              >
                {message.role === "assistant" && (
                  <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500
                                  flex items-center justify-center shadow-soft">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                {message.role === "user" && (
                  <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-surface-200 dark:bg-surface-700
                                  flex items-center justify-center">
                    <User className="w-4 h-4 text-surface-600 dark:text-surface-300" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] px-4 py-2.5 ${
                    message.role === "user"
                      ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-2xl rounded-br-md"
                      : "bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 text-surface-800 dark:text-surface-100 rounded-2xl rounded-bl-md shadow-soft-sm"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}

        {loading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500
                            flex items-center justify-center shadow-soft">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-2xl rounded-bl-md px-4 py-2.5 shadow-soft-sm">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="p-4 border-t border-surface-200 dark:border-surface-700"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="修正指示を入力..."
            className="flex-1 px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       placeholder:text-surface-400 dark:placeholder:text-surface-500
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl
                       hover:from-primary-600 hover:to-primary-700 shadow-soft hover:shadow-glow-primary
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
