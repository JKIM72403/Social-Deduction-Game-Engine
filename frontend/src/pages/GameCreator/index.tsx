import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API } from "../../services/api";
import Step1_BasicInfo from "./Step1_BasicInfo";
import Step2_Roles from "./Step2_Roles";
import Step3_Review from "./Step3_Review";
import "./GameCreator.css";

import type { GameData } from "../types";
import type { Alignment } from "../../types";

function buildDefaultGameData(): GameData {
    return {
        name: "",
        min_players: 4,
        max_players: 10,
        role_slots: [],
        phases: [
            { name: "Night", phase_type: "NIGHT", order: 0 },
            { name: "Day", phase_type: "DAY", order: 1 },
            { name: "Voting", phase_type: "VOTING", order: 2 },
        ],
        win_conditions: [
            {
                name: "Town Victory",
                winner_alignment: 0,
                order: 0,
                criteria: [{ type: "ALIGNMENT_COUNT", target: "MAFIA", count: 0 }],
            },
            {
                name: "Mafia Victory",
                winner_alignment: 0,
                order: 1,
                criteria: [{ type: "ALIGNMENT_COUNT", target: "TOWN", count: 0 }],
            },
        ],
    };
}

export default function GameCreator() {
    const [step, setStep] = useState(1);
    const [gameData, setGameData] = useState<GameData>(buildDefaultGameData());
    const navigate = useNavigate();

    useEffect(() => {
        let cancelled = false;

        const loadDefaultAlignments = async () => {
            try {
                const response = await API.get("/alignments/");
                if (cancelled) {
                    return;
                }

                const alignments: Alignment[] = response.data;
                const town = alignments.find((alignment) => alignment.name.toUpperCase() === "TOWN");
                const mafia = alignments.find((alignment) => alignment.name.toUpperCase() === "MAFIA");
                const fallback = alignments[0];

                setGameData((prev) => ({
                    ...prev,
                    win_conditions: prev.win_conditions.map((winCondition, index) => ({
                        ...winCondition,
                        winner_alignment:
                            index === 0
                                ? (town?.id || fallback?.id || 0)
                                : (mafia?.id || fallback?.id || 0),
                    })),
                }));
            } catch (e) {
                console.error(e);
                alert("Failed to load default alignments for the new template");
            }
        };

        loadDefaultAlignments();

        return () => {
            cancelled = true;
        };
    }, []);

    const nextStep = () => setStep((s) => s + 1);
    const prevStep = () => setStep((s) => s - 1);

    const saveGame = async () => {
        try {
            if (gameData.win_conditions.some((winCondition) => winCondition.winner_alignment <= 0)) {
                alert("Default win conditions are still loading. Try again in a moment.");
                return;
            }

            // Transform data for backend
            const payload = {
                name: gameData.name,
                min_players: gameData.min_players,
                max_players: gameData.max_players,
                role_slots: gameData.role_slots.map(slot => ({
                    role: slot.roleId,
                    count: slot.count
                })),
                phases: gameData.phases,
                win_conditions: gameData.win_conditions,
            };

            await API.post("/game-templates/", payload);
            alert("Game Created Successfully!");
            navigate("/");
        } catch (e) {
            console.error(e);
            alert("Failed to create game.");
        }
    };

    return (
        <div className="game-creator-container">
            <h1>Create New Game Template</h1>
            <div className="progress-bar">
                <div className={`step ${step >= 1 ? 'active' : ''}`}>1. Basic Info</div>
                <div className={`step ${step >= 2 ? 'active' : ''}`}>2. Roles</div>
                <div className={`step ${step >= 3 ? 'active' : ''}`}>3. Review</div>
            </div>

            <div className="step-content">
                {step === 1 && (
                    <Step1_BasicInfo
                        data={gameData}
                        update={(d) => setGameData({ ...gameData, ...d })}
                        onNext={nextStep}
                    />
                )}
                {step === 2 && (
                    <Step2_Roles
                        data={gameData}
                        update={(d) => setGameData({ ...gameData, ...d })}
                        onNext={nextStep}
                        onBack={prevStep}
                    />
                )}
                {step === 3 && (
                    <Step3_Review
                        data={gameData}
                        onSave={saveGame}
                        onBack={prevStep}
                    />
                )}
            </div>
        </div>
    );
}
