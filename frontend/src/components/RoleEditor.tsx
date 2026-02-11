import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import { API } from "../services/api";
import type { AbilityTemplate } from "../types";

interface Props {
    roleId?: number;
    onSave: (role: any) => void;
    onCancel: () => void;
}

export default function RoleEditor({ roleId, onSave, onCancel }: Props) {
    const [abilities, setAbilities] = useState<AbilityTemplate[]>([]);
    const [role, setRole] = useState({
        name: "",
        alignment: "TOWN",
        description: "",
        abilities: [] as number[],
    });

    useEffect(() => {
        // Fetch all abilities
        API.get("/abilities/").then(res => setAbilities(res.data));

        // If editing an existing role, fetch its data
        if (roleId) {
            API.get(`/roles/${roleId}/`).then(res => {
                const data = res.data;
                // ability_details contains objects, we need IDs for the state
                const abilityIds = data.ability_details ? data.ability_details.map((a: any) => a.id) : [];
                setRole({
                    name: data.name,
                    alignment: data.alignment,
                    description: data.description || "",
                    abilities: abilityIds
                });
            });
        }
    }, [roleId]);

    const submit = async () => {
        try {
            let res;
            if (roleId) {
                res = await API.put(`/roles/${roleId}/`, role);
            } else {
                res = await API.post("/roles/", role);
            }
            onSave(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to save role");
        }
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>
                {roleId ? "Edit Role" : "Create New Role"}
            </Typography>

            <TextField
                fullWidth
                label="Role Name"
                value={role.name}
                onChange={e => setRole({ ...role, name: e.target.value })}
                sx={{ mb: 3 }}
            />

            <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Alignment</InputLabel>
                <Select
                    value={role.alignment}
                    label="Alignment"
                    onChange={e => setRole({ ...role, alignment: e.target.value })}
                >
                    <MenuItem value="TOWN">Town</MenuItem>
                    <MenuItem value="MAFIA">Mafia</MenuItem>
                    <MenuItem value="NEUTRAL">Neutral</MenuItem>
                </Select>
            </FormControl>

            <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={role.description}
                onChange={e => setRole({ ...role, description: e.target.value })}
                sx={{ mb: 3 }}
            />

            <Typography variant="subtitle1" sx={{ mb: 1 }}>Abilities</Typography>
            <Box sx={{
                maxHeight: 200,
                overflowY: 'auto',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                p: 2,
                mb: 3
            }}>
                <FormGroup>
                    {abilities.map(a => (
                        <FormControlLabel
                            key={a.id}
                            control={
                                <Checkbox
                                    checked={role.abilities.includes(a.id)}
                                    onChange={e => {
                                        const id = Number(a.id);
                                        setRole(r => ({
                                            ...r,
                                            abilities: e.target.checked
                                                ? [...r.abilities, id]
                                                : r.abilities.filter(x => x !== id),
                                        }));
                                    }}
                                />
                            }
                            label={`${a.name} (${a.ability_type})`}
                        />
                    ))}
                </FormGroup>
                {abilities.length === 0 && (
                    <Typography variant="caption" color="text.secondary">
                        No abilities found.
                    </Typography>
                )}
            </Box>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button onClick={onCancel} variant="outlined" color="secondary">
                    Cancel
                </Button>
                <Button onClick={submit} variant="contained" color="primary">
                    {roleId ? "Update Role" : "Save Role"}
                </Button>
            </Box>
        </Box>
    );
}
