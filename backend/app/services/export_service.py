"""
Export service for formatting chat sessions, emails, and minutes.
"""

from datetime import datetime
from typing import Any
import json


class ExportService:
    """Service for formatting various content types for export."""

    def format_chat_markdown(
        self,
        session: Any,
        messages: list[Any],
        notebook_title: str | None = None,
    ) -> str:
        """Format chat session as Markdown."""
        lines = [
            f"# {session.title or 'チャット履歴'}",
            "",
        ]

        if notebook_title:
            lines.append(f"**ノートブック**: {notebook_title}")

        lines.extend([
            f"**エクスポート日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            "",
            "---",
            "",
        ])

        for msg in messages:
            role_label = "**ユーザー**" if msg.role == "user" else "**アシスタント**"
            lines.append(f"### {role_label}")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

            # Add source references if available
            if msg.source_refs:
                try:
                    refs = json.loads(msg.source_refs)
                    if refs:
                        lines.append(f"*参照元: {', '.join(refs)}*")
                        lines.append("")
                except (json.JSONDecodeError, TypeError):
                    pass

            lines.append(f"*{msg.created_at.strftime('%Y/%m/%d %H:%M')}*")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def format_chat_text(
        self,
        session: Any,
        messages: list[Any],
        notebook_title: str | None = None,
    ) -> str:
        """Format chat session as plain text."""
        lines = [
            f"チャット履歴: {session.title or 'Untitled'}",
        ]

        if notebook_title:
            lines.append(f"ノートブック: {notebook_title}")

        lines.extend([
            f"エクスポート日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            "=" * 50,
            "",
        ])

        for msg in messages:
            role_label = "[ユーザー]" if msg.role == "user" else "[アシスタント]"
            lines.append(role_label)
            lines.append(msg.content)

            # Add source references if available
            if msg.source_refs:
                try:
                    refs = json.loads(msg.source_refs)
                    if refs:
                        lines.append(f"参照元: {', '.join(refs)}")
                except (json.JSONDecodeError, TypeError):
                    pass

            lines.append(f"({msg.created_at.strftime('%Y/%m/%d %H:%M')})")
            lines.append("-" * 30)
            lines.append("")

        return "\n".join(lines)

    def format_chat_json(
        self,
        session: Any,
        messages: list[Any],
        notebook_title: str | None = None,
    ) -> dict:
        """Format chat session as JSON-serializable dict."""
        return {
            "session": {
                "id": str(session.id),
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            },
            "notebook_title": notebook_title,
            "exported_at": datetime.now().isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "source_refs": json.loads(msg.source_refs) if msg.source_refs else None,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ],
        }

    def format_email_markdown(self, email: Any, notebook_title: str | None = None) -> str:
        """Format generated email as Markdown."""
        lines = [
            f"# {email.title}",
            "",
        ]

        if notebook_title:
            lines.append(f"**ノートブック**: {notebook_title}")

        if email.topic:
            lines.append(f"**トピック**: {email.topic}")

        lines.extend([
            f"**作成日時**: {email.created_at.strftime('%Y年%m月%d日 %H:%M') if email.created_at else '不明'}",
            "",
            "---",
            "",
            "## 本文",
            "",
            email.email_body,
            "",
        ])

        return "\n".join(lines)

    def format_email_text(self, email: Any, notebook_title: str | None = None) -> str:
        """Format generated email as plain text."""
        lines = [
            f"件名: {email.title}",
        ]

        if notebook_title:
            lines.append(f"ノートブック: {notebook_title}")

        if email.topic:
            lines.append(f"トピック: {email.topic}")

        lines.extend([
            f"作成日時: {email.created_at.strftime('%Y年%m月%d日 %H:%M') if email.created_at else '不明'}",
            "=" * 50,
            "",
            email.email_body,
        ])

        return "\n".join(lines)

    def format_minute_markdown(self, minute: Any, notebook_title: str | None = None) -> str:
        """Format minute as Markdown."""
        lines = [
            f"# {minute.title}",
            "",
        ]

        if notebook_title:
            lines.append(f"**ノートブック**: {notebook_title}")

        lines.extend([
            f"**作成日時**: {minute.created_at.strftime('%Y年%m月%d日 %H:%M') if minute.created_at else '不明'}",
            "",
            "---",
            "",
        ])

        # Add summary if available
        if minute.summary:
            lines.extend([
                "## 要約",
                "",
                minute.summary,
                "",
                "---",
                "",
            ])

        lines.extend([
            "## 内容",
            "",
        ])

        # Use formatted content if available, otherwise original content
        content = minute.formatted_content or minute.content
        lines.append(content)
        lines.append("")

        return "\n".join(lines)

    def format_minute_text(self, minute: Any, notebook_title: str | None = None) -> str:
        """Format minute as plain text."""
        lines = [
            f"議事録: {minute.title}",
        ]

        if notebook_title:
            lines.append(f"ノートブック: {notebook_title}")

        lines.extend([
            f"作成日時: {minute.created_at.strftime('%Y年%m月%d日 %H:%M') if minute.created_at else '不明'}",
            "=" * 50,
            "",
        ])

        # Add summary if available
        if minute.summary:
            lines.extend([
                "[要約]",
                minute.summary,
                "",
                "-" * 30,
                "",
            ])

        lines.append("[内容]")
        content = minute.formatted_content or minute.content
        lines.append(content)

        return "\n".join(lines)

    def format_notebook_markdown(
        self,
        notebook: Any,
        sources: list[Any] | None = None,
        minutes: list[Any] | None = None,
        sessions: list[Any] | None = None,
        emails: list[Any] | None = None,
    ) -> str:
        """Format entire notebook as Markdown."""
        lines = [
            f"# {notebook.title}",
            "",
        ]

        if notebook.description:
            lines.append(f"*{notebook.description}*")
            lines.append("")

        lines.extend([
            f"**エクスポート日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            "",
            "---",
            "",
            "## 目次",
            "",
        ])

        toc_items = []
        if sources:
            toc_items.append(f"- [資料一覧](#資料一覧) ({len(sources)}件)")
        if minutes:
            toc_items.append(f"- [議事録一覧](#議事録一覧) ({len(minutes)}件)")
        if sessions:
            toc_items.append(f"- [チャット履歴](#チャット履歴) ({len(sessions)}件)")
        if emails:
            toc_items.append(f"- [生成メール](#生成メール) ({len(emails)}件)")

        lines.extend(toc_items)
        lines.extend(["", "---", ""])

        # Sources section
        if sources:
            lines.extend([
                "## 資料一覧",
                "",
            ])
            for source in sources:
                lines.append(f"### {source.title}")
                if source.summary:
                    lines.append("")
                    lines.append(f"**要約**: {source.summary}")
                lines.append("")
                lines.append(f"*アップロード日: {source.created_at.strftime('%Y/%m/%d') if source.created_at else '不明'}*")
                lines.extend(["", "---", ""])

        # Minutes section
        if minutes:
            lines.extend([
                "## 議事録一覧",
                "",
            ])
            for minute in minutes:
                lines.append(f"### {minute.title}")
                lines.append("")
                if minute.summary:
                    lines.append(f"**要約**: {minute.summary}")
                    lines.append("")
                content = minute.formatted_content or minute.content
                # Truncate if very long
                if len(content) > 1000:
                    content = content[:1000] + "..."
                lines.append(content)
                lines.append("")
                lines.append(f"*作成日: {minute.created_at.strftime('%Y/%m/%d') if minute.created_at else '不明'}*")
                lines.extend(["", "---", ""])

        # Sessions section
        if sessions:
            lines.extend([
                "## チャット履歴",
                "",
            ])
            for session in sessions:
                lines.append(f"### {session.title or '無題のチャット'}")
                lines.append("")
                lines.append(f"*作成日: {session.created_at.strftime('%Y/%m/%d') if session.created_at else '不明'}*")
                lines.append("")

                # Include messages if available
                if hasattr(session, 'messages') and session.messages:
                    for msg in session.messages[-10:]:  # Last 10 messages
                        role = "**ユーザー**" if msg.role == "user" else "**アシスタント**"
                        lines.append(f"> {role}: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
                        lines.append("")
                lines.extend(["---", ""])

        # Emails section
        if emails:
            lines.extend([
                "## 生成メール",
                "",
            ])
            for email in emails:
                lines.append(f"### {email.title}")
                lines.append("")
                if email.topic:
                    lines.append(f"**トピック**: {email.topic}")
                    lines.append("")
                lines.append(email.email_body)
                lines.append("")
                lines.append(f"*作成日: {email.created_at.strftime('%Y/%m/%d') if email.created_at else '不明'}*")
                lines.extend(["", "---", ""])

        return "\n".join(lines)


# Singleton instance
export_service = ExportService()
