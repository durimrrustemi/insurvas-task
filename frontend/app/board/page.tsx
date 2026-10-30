import { getBoard } from "@/lib/api";
import { KanbanBoard } from "@/components/KanbanBoard";

const STAGES = ["found", "contacted", "replied", "in_talks", "test_calls", "signed", "lost"];

export default async function BoardPage() {
  let board;
  try {
    board = await getBoard();
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not load board. Make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Pipeline Board</h1>
      <KanbanBoard columns={board.columns} stages={STAGES} />
    </div>
  );
}
