import { useEffect, useState } from "react";
import { API } from "../../services/api";
import type { GameData, RoleSlot } from "../types";
import RoleEditor from "../../components/RoleEditor";

interface Props {
    data: GameData;
    update: (data: Partial<GameData>) => void;
    onNext: () => void;
    onBack: () => void;
}

export default function Step2_Roles({ data, update, onNext, onBack }: Props) {
    const [availableRoles, setAvailableRoles] = useState<any[]>([]);
    const [isCreatingRole, setIsCreatingRole] = useState(false);

    useEffect(() => {
        loadRoles();
    }, []);

    const loadRoles = () => {
        API.get("/roles/").then(res => setAvailableRoles(res.data));
    };

    const addRoleToGame = (role: any) => {
        const existing = data.role_slots.find(s => s.roleId === role.id);
        if (existing) {
            update({
                role_slots: data.role_slots.map(s =>
                    s.roleId === role.id ? { ...s, count: s.count + 1 } : s
                )
            });
        } else {
            update({
                role_slots: [...data.role_slots, { roleId: role.id, roleName: role.name, count: 1 }]
            });
        }
    };

    const removeRoleFromGame = (roleId: number) => {
        update({
            role_slots: data.role_slots.filter(s => s.roleId !== roleId)
        });
    };

    const updateCount = (roleId: number, count: number) => {
        if (count <= 0) {
            removeRoleFromGame(roleId);
        } else {
            update({
                role_slots: data.role_slots.map(s =>
                    s.roleId === roleId ? { ...s, count } : s
                )
            });
        }
    };

    if (isCreatingRole) {
        return (
            <RoleEditor
                onSave={(newRole) => {
                    setAvailableRoles([...availableRoles, newRole]);
                    addRoleToGame(newRole);
                    setIsCreatingRole(false);
                }}
                onCancel={() => setIsCreatingRole(false)}
            />
        );
    }

    const totalRoles = data.role_slots.reduce((sum, s) => sum + s.count, 0);

    return (
        <div className="wizard-step">
            <h2>Manage Roles</h2>
            <div className="role-management">
                <div className="available-roles">
                    <h3>Available Roles</h3>
                    <button onClick={() => setIsCreatingRole(true)} className="btn-secondary small">+ Create New Role</button>
                    <ul className="role-list">
                        {availableRoles.map(role => (
                            <li key={role.id}>
                                <span>{role.name} ({role.alignment})</span>
                                <button onClick={() => addRoleToGame(role)}>Add</button>
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="selected-roles">
                    <h3>Selected Roles ({totalRoles})</h3>
                    {data.role_slots.length === 0 ? <p>No roles selected.</p> : (
                        <ul className="role-list">
                            {data.role_slots.map(slot => (
                                <li key={slot.roleId}>
                                    <span>{slot.roleName}</span>
                                    <div className="count-controls">
                                        <button onClick={() => updateCount(slot.roleId, slot.count - 1)}>-</button>
                                        <span>{slot.count}</span>
                                        <button onClick={() => updateCount(slot.roleId, slot.count + 1)}>+</button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                    {totalRoles < data.min_players && (
                        <p className="warning">Need at least {data.min_players} roles.</p>
                    )}
                    {totalRoles > data.max_players && (
                        <p className="warning">Too many roles (max {data.max_players}).</p>
                    )}
                </div>
            </div>

            <div className="actions">
                <button onClick={onBack} className="btn-secondary">Back</button>
                <button
                    disabled={totalRoles < data.min_players || totalRoles > data.max_players}
                    onClick={onNext}
                    className="btn-primary"
                >
                    Next
                </button>
            </div>
        </div>
    );
}
