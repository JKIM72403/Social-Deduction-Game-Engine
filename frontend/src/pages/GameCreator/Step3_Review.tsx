import type { GameData } from "./types";

interface Props {
    data: GameData;
    onSave: () => void;
    onBack: () => void;
}

export default function Step3_Review({ data, onSave, onBack }: Props) {
    const totalRoles = data.role_slots.reduce((sum, s) => sum + s.count, 0);

    return (
        <div className="wizard-step">
            <h2>Review Game Template</h2>

            <div className="review-section">
                <h3>Basic Info</h3>
                <p><strong>Name:</strong> {data.name}</p>
                <p><strong>Min Players:</strong> {data.min_players}</p>
                <p><strong>Max Players:</strong> {data.max_players}</p>
            </div>

            <div className="review-section">
                <h3>Roles ({totalRoles})</h3>
                <ul>
                    {data.role_slots.map(slot => (
                        <li key={slot.roleId}>
                            {slot.roleName} x{slot.count}
                        </li>
                    ))}
                </ul>
            </div>

            <div className="actions">
                <button onClick={onBack} className="btn-secondary">Back</button>
                <button onClick={onSave} className="btn-primary">Create Game</button>
            </div>
        </div>
    );
}
