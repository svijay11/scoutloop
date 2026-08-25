import LeadCard from "./LeadCard.jsx";
import "../styles/board.css";

const LANES = [
  {
    id: "reviewing",
    label: "Reviewing",
    match: (stage) => stage !== "DISQUALIFIED",
  },
  {
    id: "disqualified",
    label: "Disqualified",
    match: (stage) => stage === "DISQUALIFIED",
  },
];

export default function Board({ leads, selectedId, onSelect, readOnly = false }) {
  return (
    <div className={`board ${readOnly ? "is-readonly" : ""}`}>
      {LANES.map((lane) => {
        const cards = leads.filter((lead) => lane.match(lead.stage));
        return (
          <section className="board-col" key={lane.id}>
            <header className="board-col-head">
              <span>{lane.label}</span>
              <span className="board-col-count">{cards.length}</span>
            </header>
            <div className="board-col-body">
              {cards.map((lead) => (
                <LeadCard
                  key={lead.id}
                  lead={lead}
                  selected={selectedId === lead.id}
                  onSelect={readOnly ? undefined : onSelect}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
