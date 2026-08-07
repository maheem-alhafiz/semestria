"use client";

import { useState } from "react";

import { useAssessmentsStore } from "@/store/assessmentsStore";

export function TodosSection() {
  const todos = useAssessmentsStore((s) => s.todos);
  const courses = useAssessmentsStore((s) => s.courses);
  const term = useAssessmentsStore((s) => s.term);
  const addTodo = useAssessmentsStore((s) => s.addTodo);
  const editTodo = useAssessmentsStore((s) => s.editTodo);
  const removeTodo = useAssessmentsStore((s) => s.removeTodo);

  const [text, setText] = useState("");
  const [courseId, setCourseId] = useState<string>(""); // "" = general
  const [adding, setAdding] = useState(false);

  const pending = todos.filter((t) => !t.is_done);
  const done = todos.filter((t) => t.is_done);

  function courseLabel(id: number | null) {
    if (id === null) return null;
    const c = courses.find((c) => c.course_id === id);
    return c ? `${c.subject} ${c.course_number}` : null;
  }

  async function handleAdd() {
    if (!term || !text.trim()) return;
    setAdding(true);
    try {
      await addTodo({
        term_code: term.term_code,
        course_id: courseId ? Number(courseId) : null,
        text: text.trim(),
      });
      setText("");
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="rounded-2xl border border-hairline bg-panel p-4">
      <h2 className="text-sm font-semibold text-paper">To-do</h2>

      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="e.g. Finish last page of chapter 5"
          className="min-w-0 flex-1 rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <select
          value={courseId}
          onChange={(e) => setCourseId(e.target.value)}
          className="w-28 shrink-0 rounded-xl border border-hairline bg-elevated px-2 py-2 text-xs text-paper focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">General</option>
          {courses.map((c) => (
            <option key={c.course_id} value={c.course_id}>
              {c.subject} {c.course_number}
            </option>
          ))}
        </select>
        <button
          onClick={handleAdd}
          disabled={adding || !text.trim()}
          className="shrink-0 rounded-xl bg-accent px-3 py-2 text-sm font-medium text-canvas disabled:opacity-40"
        >
          Add
        </button>
      </div>

      <div className="mt-3 space-y-1">
        {pending.length === 0 && done.length === 0 && (
          <p className="text-sm text-muted">Nothing here yet.</p>
        )}
        {pending.map((todo) => (
          <div key={todo.id} className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 hover:bg-elevated">
            <input
              type="checkbox"
              checked={todo.is_done}
              onChange={(e) => editTodo(todo.id, { is_done: e.target.checked })}
              className="h-4 w-4 shrink-0 rounded border-hairline accent-[var(--accent)]"
            />
            <span className="min-w-0 flex-1 truncate text-sm text-paper">{todo.text}</span>
            {courseLabel(todo.course_id) && (
              <span className="shrink-0 rounded-full bg-elevated px-2 py-0.5 text-[11px] text-muted">
                {courseLabel(todo.course_id)}
              </span>
            )}
            <button
              onClick={() => removeTodo(todo.id)}
              className="shrink-0 text-muted hover:text-danger"
              aria-label="Delete to-do"
            >
              ×
            </button>
          </div>
        ))}
        {done.length > 0 && (
          <details className="mt-1">
            <summary className="cursor-pointer text-xs text-muted">{done.length} done</summary>
            <div className="mt-1 space-y-1">
              {done.map((todo) => (
                <div key={todo.id} className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 hover:bg-elevated">
                  <input
                    type="checkbox"
                    checked={todo.is_done}
                    onChange={(e) => editTodo(todo.id, { is_done: e.target.checked })}
                    className="h-4 w-4 shrink-0 rounded border-hairline accent-[var(--accent)]"
                  />
                  <span className="min-w-0 flex-1 truncate text-sm text-muted line-through">{todo.text}</span>
                  {courseLabel(todo.course_id) && (
                    <span className="shrink-0 rounded-full bg-elevated px-2 py-0.5 text-[11px] text-muted">
                      {courseLabel(todo.course_id)}
                    </span>
                  )}
                  <button
                    onClick={() => removeTodo(todo.id)}
                    className="shrink-0 text-muted hover:text-danger"
                    aria-label="Delete to-do"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
