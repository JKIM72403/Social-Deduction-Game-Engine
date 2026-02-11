import { API } from "../services/api";

type GameTemplate = {
    id: number;
    name: string;
    min_players: number;
    max_players: number;
};

export default function Home() {
    const [games, setGames] = useState<GameTemplate[]>([]);

    useEffect(() => {
        API.get("/game-templates/")
            .then((res) => setGames(res.data))
            .catch((err) => console.error("Failed to load games", err));
    }, []);

    return (
        <div>
            <h1>Game Templates</h1>
            <p>Select a game to modify or create a new one.</p>

            <div style={{ marginTop: "2rem" }}>
                {games.length === 0 ? (
                    <p>No games found. Create one!</p>
                ) : (
                    <ul style={{ listStyle: "none", padding: 0 }}>
                        {games.map((game) => (
                            <li key={game.id} style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem", borderRadius: "8px" }}>
                                <h3>{game.name}</h3>
                                <p>Players: {game.min_players} - {game.max_players}</p>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
