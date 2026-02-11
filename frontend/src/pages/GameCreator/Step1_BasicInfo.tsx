import type { GameData } from "./types";

interface Props {
    data: GameData;
    update: (data: Partial<GameData>) => void;
    onNext: () => void;
}

export default function Step1_BasicInfo({ data, update, onNext }: Props) {
    const isValid = data.name.length > 0 && data.max_players >= data.min_players;

    return (
        <div className="wizard-step">
            <h2>Basic Information</h2>

            <div className="form-group">
                <label>Game Name</label>
                <input
                    type="text"
                    value={data.name}
                    onChange={(e) => update({ name: e.target.value })}
                    placeholder="e.g. Classic Mafia"
                />
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label>Min Players</label>
                    <input
                        type="number"
                        value={data.min_players}
                        onChange={(e) => update({ min_players: parseInt(e.target.value) })}
                        min={3}
                    />
                </div>
                <div className="form-group">
                    <label>Max Players</label>
                    <input
                        type="number"
                        value={data.max_players}
                        onChange={(e) => update({ max_players: parseInt(e.target.value) })}
                        min={data.min_players}
                    />
                </div>
            </div>

            <div className="actions">
                <button disabled={!isValid} onClick={onNext} className="btn-primary">Next</button>
            </div>
        </div>
    );
}
