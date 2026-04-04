import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import CircleIcon from '@mui/icons-material/Circle';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import type { DropResult } from '@hello-pangea/dnd';
import type { GameData, Phase } from '../types';

interface SidebarProps {
    gameData: GameData;
    onSelect: (type: 'GAME_SETTINGS' | 'ROLE' | 'PHASE' | 'WIN_CONDITION', id?: number, index?: number) => void;
    onAddRole: () => void;
    onAddPhase: () => void;
    onAddWinCondition: () => void;
    onReorderPhases: (newPhases: Phase[]) => void;
}

interface SidebarSectionProps {
    title: string;
    droppableId?: string;
    items: { label: string; id?: number; index: number }[];
    onItemClick: (id?: number, index?: number) => void;
    onAdd?: () => void;
    isDraggable?: boolean;
}

const SidebarSection = ({ title, droppableId, items, onItemClick, onAdd, isDraggable }: SidebarSectionProps) => (
    <Box sx={{ mb: 3 }}>
        <Box sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 1,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            px: 1,
            py: 0.5,
            borderRadius: 1
        }}>
            <Typography variant="subtitle2" fontWeight={600}>
                {title}
            </Typography>
            {onAdd && (
                <IconButton
                    size="small"
                    sx={{ p: 0.5 }}
                    onClick={(e) => { e.stopPropagation(); onAdd(); }}
                >
                    <AddIcon fontSize="small" />
                </IconButton>
            )}
        </Box>

        {isDraggable && droppableId ? (
            <Droppable droppableId={droppableId}>
                {(provided) => (
                    <List
                        {...provided.droppableProps}
                        ref={provided.innerRef}
                        disablePadding
                    >
                        {items.map((item, index) => (
                            <Draggable
                                key={`${droppableId}-${item.id || index}`}
                                draggableId={`${droppableId}-${item.id || index}`}
                                index={index}
                            >
                                {(provided, snapshot) => (
                                    <ListItem
                                        ref={provided.innerRef}
                                        {...provided.draggableProps}
                                        disablePadding
                                        sx={{
                                            mb: 0.5,
                                            cursor: 'pointer',
                                            bgcolor: snapshot.isDragging ? 'action.selected' : 'transparent',
                                            '&:hover': { bgcolor: 'action.hover' },
                                            display: 'flex',
                                            alignItems: 'center',
                                            borderRadius: 1
                                        }}
                                        onClick={() => onItemClick(item.id, item.index)}
                                    >
                                        <Box {...provided.dragHandleProps} sx={{ display: 'flex', alignItems: 'center', ml: 1, color: 'text.disabled' }}>
                                            <DragIndicatorIcon sx={{ fontSize: 18 }} />
                                        </Box>
                                        <ListItemText
                                            primary={item.label}
                                            primaryTypographyProps={{
                                                variant: 'body2',
                                                fontSize: '0.85rem',
                                                sx: { ml: 1, py: 0.5 }
                                            }}
                                        />
                                    </ListItem>
                                )}
                            </Draggable>
                        ))}
                        {provided.placeholder}
                    </List>
                )}
            </Droppable>
        ) : (
            <List disablePadding>
                {items.map((item, index) => (
                    <ListItem
                        key={index}
                        disablePadding
                        sx={{
                            mb: 0.5,
                            cursor: 'pointer',
                            '&:hover': { bgcolor: 'action.hover' }
                        }}
                        onClick={() => onItemClick(item.id, item.index)}
                    >
                        <CircleIcon sx={{ fontSize: 6, color: 'text.secondary', mr: 1, ml: 1 }} />
                        <ListItemText
                            primary={item.label}
                            primaryTypographyProps={{ variant: 'body2', fontSize: '0.85rem' }}
                        />
                    </ListItem>
                ))}
            </List>
        )}
        {items.length === 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                No items
            </Typography>
        )}
    </Box>
);

const Sidebar = ({
    gameData,
    onSelect,
    onAddRole,
    onAddPhase,
    onAddWinCondition,
    onReorderPhases
}: SidebarProps) => {

    const onDragEnd = (result: DropResult) => {
        const { source, destination } = result;
        if (!destination) return;
        if (source.droppableId === destination.droppableId && source.index === destination.index) return;

        if (source.droppableId === 'phases') {
            const newPhases = Array.from(gameData.phases);
            const [reorderedItem] = newPhases.splice(source.index, 1);
            newPhases.splice(destination.index, 0, reorderedItem);

            // Update order numbers
            const updated = newPhases.map((p, i) => ({ ...p, order: i }));
            onReorderPhases(updated);
        }
    };

    return (
        <Box sx={{
            width: 280,
            bgcolor: 'background.default',
            borderRight: '1px solid',
            borderColor: 'divider',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto'
        }}>
            <Button
                variant="contained"
                color="primary"
                fullWidth
                sx={{ mb: 3, fontWeight: 'bold' }}
                onClick={() => onSelect('GAME_SETTINGS')}
            >
                Game Settings
            </Button>

            <DragDropContext onDragEnd={onDragEnd}>
                <SidebarSection
                    title="Roles in Game"
                    items={gameData.role_slots.map((slot, idx) => ({
                        label: `${slot.roleName} (x${slot.count})${slot.isDefault ? ' (default)' : ''}`,
                        id: slot.roleId,
                        index: idx
                    }))}
                    onItemClick={(id) => onSelect('ROLE', id)}
                    onAdd={onAddRole}
                />

                <SidebarSection
                    title="Phases"
                    droppableId="phases"
                    isDraggable={true}
                    items={gameData.phases.map((p, idx) => ({
                        label: p.name,
                        id: p.id,
                        index: idx
                    }))}
                    onItemClick={(id, index) => onSelect('PHASE', id, index)}
                    onAdd={onAddPhase}
                />

                <SidebarSection
                    title="Win Conditions"
                    items={gameData.win_conditions.map((wc, idx) => ({
                        label: wc.name,
                        id: wc.id,
                        index: idx
                    }))}
                    onItemClick={(id, index) => onSelect('WIN_CONDITION', id, index)}
                    onAdd={onAddWinCondition}
                />
            </DragDropContext>
        </Box>
    );
};

export default Sidebar;
