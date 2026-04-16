import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Chip from '@mui/material/Chip';
import Popover from '@mui/material/Popover';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { API } from "../services/api";
import type { AbilityTemplate, Alignment, RoleTemplate } from "../types";
import { COLORS } from '../constants/colors';


interface Props {
    roleId?: number;
    gameId?: number;
    onSave: (role: RoleTemplate, originalId?: number) => void;
    onCancel: () => void;
}

const selectedChipSx = {
    borderColor: COLORS.BORDER_HIGHLIGHT,
    borderWidth: 2,
    backgroundColor: 'rgba(34, 197, 94, 0.08)',
    '&:hover': {
        backgroundColor: 'rgba(34, 197, 94, 0.15)',
    },
};

const unselectedChipSx = {
    borderColor: COLORS.BORDER_DEFAULT,
    borderWidth: 1,
    '&:hover': {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
};

export default function RoleEditor({ roleId, gameId, onSave, onCancel }: Props) {
    const [abilities, setAbilities] = useState<AbilityTemplate[]>([]);
    const [alignments, setAlignments] = useState<Alignment[]>([]);
    const [role, setRole] = useState({
        name: "",
        alignment: 0,
        description: "",
        abilities: [] as number[],
    });

    const [popoverAnchor, setPopoverAnchor] = useState<HTMLElement | null>(null);
    const [popoverAbilityId, setPopoverAbilityId] = useState<number | null>(null);

    useEffect(() => {
        let cancelled = false;

        const loadEditorState = async () => {
            try {
                const [abilitiesRes, alignmentsRes] = await Promise.all([
                    API.get("/abilities/"),
                    API.get("/alignments/", { params: gameId ? { game_template: gameId } : undefined }),
                ]);
                if (cancelled) {
                    return;
                }

                setAbilities(abilitiesRes.data);
                const loadedAlignments: Alignment[] = alignmentsRes.data;
                setAlignments(loadedAlignments);

                if (roleId) {
                    const roleRes = await API.get(`/roles/${roleId}/`);
                    if (cancelled) {
                        return;
                    }
                    const data = roleRes.data;
                    const abilityIds = data.ability_details ? data.ability_details.map((a: any) => a.id) : [];
                    setRole({
                        name: data.name,
                        alignment: data.alignment,
                        description: data.description || "",
                        abilities: abilityIds,
                    });
                    return;
                }

                const town = loadedAlignments.find((a) => a.name.toUpperCase() === 'TOWN');
                setRole((r) => ({ ...r, alignment: town ? town.id : loadedAlignments[0]?.id || 0 }));
            } catch (e) {
                console.error(e);
                alert("Failed to load role editor data");
            }
        };

        loadEditorState();

        return () => {
            cancelled = true;
        };
    }, [roleId, gameId]);

    const toggleAbility = (id: number) => {
        setRole(r => ({
            ...r,
            abilities: r.abilities.includes(id)
                ? r.abilities.filter(x => x !== id)
                : [...r.abilities, id],
        }));
    };

    const handleInfoClick = (event: React.MouseEvent<HTMLElement | SVGSVGElement>, abilityId: number) => {
        event.stopPropagation();
        setPopoverAnchor(event.currentTarget as HTMLElement);
        setPopoverAbilityId(abilityId);
    };

    const handlePopoverClose = () => {
        setPopoverAnchor(null);
        setPopoverAbilityId(null);
    };

    const popoverAbility = abilities.find(a => a.id === popoverAbilityId);


    const submit = async () => {
        if (!role.name.trim()) {
            alert("Role name is required");
            return;
        }

        if (!role.alignment || role.alignment <= 0) {
            alert("A valid alignment is required");
            return;
        }

        try {
            let res;
            const originalId = roleId;
            const payload = gameId ? { ...role, game_template: gameId } : role;
            if (roleId) {
                res = await API.put(`/roles/${roleId}/`, payload);
            } else {
                res = await API.post("/roles/", payload);
            }
            // Pass both the updated role and the original ID to handle cloning/migration
            onSave(res.data, originalId);
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
                    onChange={e => setRole({ ...role, alignment: Number(e.target.value) })}
                >
                    {alignments.map(a => (
                        <MenuItem key={a.id} value={a.id}>{a.name}</MenuItem>
                    ))}
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
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                p: 2,
                mb: 3,
                minHeight: 60,
            }}>
                {abilities.map(a => {
                    const isSelected = role.abilities.includes(a.id);
                    return (
                        <Chip
                            key={a.id}
                            label={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    {a.name}
                                    <InfoOutlinedIcon
                                        fontSize="small"
                                        onClick={(e) => handleInfoClick(e, a.id)}
                                        sx={{ cursor: 'pointer', ml: 0.5 }}
                                    />
                                </Box>
                            }
                            variant="outlined"
                            onClick={() => toggleAbility(a.id)}
                            sx={{
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                ...(isSelected ? selectedChipSx : unselectedChipSx),
                            }}
                        />

                    );
                })}
                {abilities.length === 0 && (
                    <Typography variant="caption" color="text.secondary">
                        No abilities found.
                    </Typography>
                )}
            </Box>

            <Popover
                open={Boolean(popoverAnchor)}
                anchorEl={popoverAnchor}
                onClose={handlePopoverClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                transformOrigin={{ vertical: 'top', horizontal: 'center' }}
                slotProps={{
                    paper: {
                        sx: {
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            borderRadius: 2,
                        }
                    }
                }}
            >
                {popoverAbility && (
                    <Box sx={{ p: 2, maxWidth: 280 }}>
                        <Typography variant="subtitle2">{popoverAbility.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                            {popoverAbility.ability_type} &middot; {popoverAbility.phase}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                            {popoverAbility.description || "No description available."}
                        </Typography>
                    </Box>
                )}
            </Popover>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 4 }}>
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
