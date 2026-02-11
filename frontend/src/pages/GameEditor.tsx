import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Navbar from '../components/navbar';
import Sidebar from '../components/sidebar';
import EditPanel from '../components/edit-panel';
import { API } from '../services/api';
import type { GameData, RoleSlot } from '../types';
import { useNavigate, useParams } from 'react-router-dom';

type Selection = { type: 'GAME_SETTINGS' } | { type: 'ROLE', roleId: number } | { type: 'NEW_ROLE' } | { type: 'EDIT_ROLE_DETAILS', roleId: number } | null;

const GameEditor = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const [gameData, setGameData] = useState<GameData>({
        name: "New Game",
        min_players: 4,
        max_players: 10,
        role_slots: []
    });
    const [selection, setSelection] = useState<Selection>({ type: 'GAME_SETTINGS' });

    useEffect(() => {
        if (id) {
            API.get(`/game-templates/${id}/`)
                .then(res => {
                    const data = res.data;
                    // Transform API response to internal GameData format
                    const role_slots = data.role_slots.map((s: any) => ({
                        roleId: s.role,
                        roleName: s.role_details ? s.role_details.name : "Unknown Role",
                        count: s.count
                    }));
                    setGameData({
                        name: data.name,
                        min_players: data.min_players,
                        max_players: data.max_players,
                        role_slots: role_slots
                    });
                })
                .catch(err => {
                    console.error("Failed to fetch game", err);
                    alert("Could not load game details.");
                    navigate("/");
                });
        }
    }, [id, navigate]);

    const handleUpdateGame = (data: Partial<GameData>) => {
        setGameData(prev => ({ ...prev, ...data }));
    };

    const handleRoleSaved = (role: any) => {
        // If it's a new role (not in slots), add it.
        // If it's an existing role, just update name in slots if needed.
        setGameData(prev => {
            const existingSlotIndex = prev.role_slots.findIndex(s => s.roleId === role.id);
            if (existingSlotIndex >= 0) {
                // Update name if changed
                const newSlots = [...prev.role_slots];
                newSlots[existingSlotIndex] = { ...newSlots[existingSlotIndex], roleName: role.name };
                return { ...prev, role_slots: newSlots };
            } else {
                // Add new role slot
                const newSlot: RoleSlot = {
                    roleId: role.id,
                    roleName: role.name,
                    count: 1
                };
                return { ...prev, role_slots: [...prev.role_slots, newSlot] };
            }
        });

        // Go back to the role slot view
        setSelection({ type: 'ROLE', roleId: role.id });
    };

    const handleSaveGame = async () => {
        try {
            const payload = {
                name: gameData.name,
                min_players: gameData.min_players,
                max_players: gameData.max_players,
                role_slots: gameData.role_slots.map(slot => ({
                    role: slot.roleId,
                    count: slot.count
                }))
            };

            if (id) {
                await API.put(`/game-templates/${id}/`, payload);
                alert("Game Updated Successfully!");
            } else {
                await API.post("/game-templates/", payload);
                alert("Game Created Successfully!");
            }
            navigate("/");
        } catch (e) {
            console.error(e);
            alert("Failed to save game.");
        }
    };

    return (
        <Box sx={{
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            bgcolor: 'background.default'
        }}>
            <Navbar />
            {/* Note: Navbar currently has static buttons, we might want to move Save button there later. For now I'll put a Save button in a visible spot or assume EditPanel handles it? 
                Actually the user said "GameCreator to essentially be the same as the game editor". 
                I'll add a Save button to the main area for now.
            */}

            <Box sx={{
                flex: 1,
                display: 'flex',
                overflow: 'hidden'
            }}>
                <Sidebar
                    gameData={gameData}
                    onSelect={(type, id) => setSelection(type === 'ROLE' && id ? { type, roleId: id } : { type: type as any })}
                    onAddRole={() => setSelection({ type: 'NEW_ROLE' })}
                />

                <Box component="main" sx={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    background: 'radial-gradient(circle at center, #1e293b 0%, #0f172a 100%)',
                    flexDirection: 'column',
                    gap: 2
                }}>
                    <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="text.primary" fontWeight={600}>
                            {gameData.name}
                        </Typography>
                        <Typography variant="subtitle1" color="text.secondary">
                            {gameData.min_players} - {gameData.max_players} Players
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                            {gameData.role_slots.length} Roles Configured
                        </Typography>
                    </Box>

                    <Box>
                        <button className="btn-primary" onClick={handleSaveGame} style={{ padding: '10px 20px', fontSize: '1rem', cursor: 'pointer' }}>
                            Save Game
                        </button>
                    </Box>
                </Box>

                <EditPanel
                    selection={selection}
                    gameData={gameData}
                    onUpdateGame={handleUpdateGame}
                    onSaveRole={handleRoleSaved}
                    onCancel={() => setSelection({ type: 'GAME_SETTINGS' })}
                    onEditRoleDetails={(roleId) => setSelection({ type: 'EDIT_ROLE_DETAILS', roleId })}
                />
            </Box>
        </Box>
    );
};

export default GameEditor;
