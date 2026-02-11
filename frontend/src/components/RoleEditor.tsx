import { useEffect, useState } from "react";
import { API } from "../services/api";

interface Props {
    onSave: (role: any) => void;
    onCancel: () => void;
}

export default function RoleEditor({ onSave, onCancel }: Props) {
    const [abilities, setAbilities] = useState<any[]>([]);
    const [role, setRole] = useState({
        name: "",
        alignment: "TOWN",
        description: "",
        abilities: [] as number[],
    });

    useEffect(() => {
        API.get("/abilities/").then(res => setAbilities(res.data));
    }, []);

    const submit = async () => {
        try {
            const res = await API.post("/roles/", role);
            onSave(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to create role");
        }
    };

    return (
        <div className="role-editor">
            <h3>Create New Role</h3>

            <div className="form-group">
                <label>Role Name</label>
                <input
                    placeholder="Role Name"
                    value={role.name}
                    onChange={e => setRole({ ...role, name: e.target.value })}
                />
            </div>

            <div className="form-group">
                <label>Alignment</label>
                <select value={role.alignment} onChange={e => setRole({ ...role, alignment: e.target.value })}>
                    <option value="TOWN">Town</option>
                    <option value="MAFIA">Mafia</option>
                    <option value="NEUTRAL">Neutral</option>
                </select>
            </div>

            <div className="form-group">
                <label>Description</label>
                <textarea
                    placeholder="Description"
                    value={role.description}
                    onChange={e => setRole({ ...role, description: e.target.value })}
                />
            </div>

            <div className="form-group">
                <h4>Abilities</h4>
                <div className="abilities-list">
                    {abilities.map(a => (
                        <label key={a.id} className="checkbox-label">
                            <input
                                type="checkbox"
                                value={a.id}
                                checked={role.abilities.includes(a.id)}
                                onChange={e => {
                                    const id = Number(e.target.value);
                                    setRole(r => ({
                                        ...r,
                                        abilities: e.target.checked
                                            ? [...r.abilities, id]
                                            : r.abilities.filter(x => x !== id),
                                    }));
                                }}
                            />
                            {a.name} ({a.ability_type})
                        </label>
                    ))}
                </div>
            </div>

            <div className="actions">
                <button onClick={submit} className="btn-primary">Save Role</button>
                <button onClick={onCancel} className="btn-secondary">Cancel</button>
            </div>
        </div>
    );
}
