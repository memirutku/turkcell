"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div
      className="prose prose-sm max-w-none
        prose-headings:text-sm prose-headings:font-semibold prose-headings:mb-2
        prose-p:mb-2 prose-p:leading-relaxed
        prose-ul:mb-2 prose-ol:mb-2
        prose-table:text-xs
        prose-th:px-2 prose-th:py-1 prose-th:bg-gray-50 prose-th:font-semibold
        prose-td:px-2 prose-td:py-1 prose-td:border-t prose-td:border-gray-200
        prose-code:text-xs prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded
        prose-a:text-turkcell-blue prose-a:underline"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
