import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useAuth } from "../contexts/AuthContext";
import { getWebSocketSessionUrl } from "../services/api";
import { getSessionSnapshot, setSessionReady, startSession } from "../services/sessions";
import type { SessionParticipant, SessionSnapshot, SessionSocketMessage } from "../types";

type SocketStatus = "connecting" | "connected" | "disconnected";

function getParticipantStatus(participant: SessionParticipant) {
  if (!participant.is_connected) return { label: "Offline", color: "default" as const };
  if (participant.is_ready) return { label: "Ready", color: "success" as const };
  return { label: "Waiting", color: "warning" as const };
}

export default function SessionLobby() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const numericSessionId = Number(sessionId);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("connecting");
  const [readySubmitting, setReadySubmitting] = useState(false);
  const [startSubmitting, setStartSubmitting] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(numericSessionId)) {
      setError("That session link is invalid.");
      setLoading(false);
      return;
    }

    let active = true;

    getSessionSnapshot(numericSessionId)
      .then((data) => {
        if (!active) return;
        setSnapshot(data);
        setLoading(false);
      })
      .catch((err: any) => {
        if (!active) return;
        const message =
          err?.response?.data?.error ||
          "Unable to load this session right now.";
        setError(message);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [numericSessionId]);

  useEffect(() => {
    if (!Number.isFinite(numericSessionId) || !localStorage.getItem("token")) {
      return;
    }

    setSocketStatus("connecting");
    const socket = new WebSocket(getWebSocketSessionUrl(numericSessionId));

    socket.onopen = () => {
      setSocketStatus("connected");
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as SessionSocketMessage;
      if (message.type === "session.snapshot") {
        setSnapshot(message.snapshot);
      } else if (message.type === "error") {
        setActionError(message.message);
      }
    };

    socket.onclose = () => {
      setSocketStatus("disconnected");
    };

    socket.onerror = () => {
      setSocketStatus("disconnected");
    };

    return () => {
      socket.close();
    };
  }, [numericSessionId]);

  const me = useMemo(
    () => snapshot?.participants.find((participant) => participant.user_id === user?.id) ?? null,
    [snapshot, user?.id],
  );

  const isHost = snapshot?.session.host_user_id === user?.id;

  const handleToggleReady = async () => {
    if (!snapshot || !me) return;

    setReadySubmitting(true);
    setActionError(null);
    try {
      const updated = await setSessionReady(snapshot.session.id, !me.is_ready);
      setSnapshot(updated);
      setActionNotice(!me.is_ready ? "You are marked ready." : "You are marked not ready.");
    } catch (err: any) {
      const message =
        err?.response?.data?.error ||
        "Unable to update your ready state right now.";
      setActionError(message);
    } finally {
      setReadySubmitting(false);
    }
  };

  const handleStartSession = async () => {
    if (!snapshot) return;

    setStartSubmitting(true);
    setActionError(null);
    try {
      const updated = await startSession(snapshot.session.id);
      setSnapshot(updated);
      setActionNotice("The session has started.");
    } catch (err: any) {
      const message =
        err?.response?.data?.error ||
        "Unable to start the session right now.";
      setActionError(message);
    } finally {
      setStartSubmitting(false);
    }
  };

  const handleCopyJoinCode = async () => {
    if (!snapshot) return;

    try {
      await navigator.clipboard.writeText(snapshot.session.join_code);
      setActionNotice("Join code copied to clipboard.");
    } catch {
      setActionError("Unable to copy the join code from this browser.");
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", flexGrow: 1 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !snapshot) {
    return (
      <Box sx={{ p: 4, maxWidth: 720, mx: "auto" }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || "Session not found."}
        </Alert>
        <Button variant="outlined" onClick={() => navigate("/multiplayer")}>
          Back to Lobby Hub
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4, maxWidth: 1100, mx: "auto", display: "flex", flexDirection: "column", gap: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={3}
          alignItems={{ xs: "flex-start", md: "center" }}
          justifyContent="space-between"
        >
          <Box>
            <Typography variant="overline" color="secondary.main">
              Multiplayer Session
            </Typography>
            <Typography variant="h4" fontWeight={700}>
              {snapshot.session.template_name}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Host: {snapshot.session.host_username || "Unknown"} | Status: {snapshot.session.status}
            </Typography>
          </Box>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
            <Chip label={`Socket: ${socketStatus}`} color={socketStatus === "connected" ? "success" : socketStatus === "connecting" ? "warning" : "default"} />
            <Chip label={`Code: ${snapshot.session.join_code}`} color="secondary" />
            <Button variant="outlined" onClick={handleCopyJoinCode}>
              Copy Join Code
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.2fr 0.8fr" }, gap: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Lobby Roster
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {snapshot.session.ready_count} of {snapshot.session.participant_count} players ready
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <List disablePadding>
              {snapshot.participants.map((participant) => {
                const status = getParticipantStatus(participant);
                const isCurrentUser = participant.user_id === user?.id;
                return (
                  <ListItem
                    key={participant.id}
                    disablePadding
                    sx={{
                      py: 1.25,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      borderBottom: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <ListItemText
                      primary={`${participant.display_name}${isCurrentUser ? " (You)" : ""}`}
                      secondary={
                        participant.role_name
                          ? `${participant.role_name}${participant.role_alignment ? ` - ${participant.role_alignment}` : ""}`
                          : `${participant.username}${participant.is_alive ? "" : " - Eliminated"}`
                      }
                      primaryTypographyProps={{ fontWeight: isCurrentUser ? 700 : 500 }}
                    />
                    <Stack direction="row" spacing={1} alignItems="center">
                      {participant.user_id === snapshot.session.host_user_id && (
                        <Chip label="Host" size="small" color="primary" />
                      )}
                      <Chip label={status.label} size="small" color={status.color} />
                    </Stack>
                  </ListItem>
                );
              })}
            </List>
          </CardContent>
        </Card>

        <Stack spacing={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Your Controls
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Ready up while the lobby is open. Once everyone is set, the host can start the session.
              </Typography>

              <Stack spacing={1.5}>
                <Button
                  variant={me?.is_ready ? "outlined" : "contained"}
                  color={me?.is_ready ? "warning" : "success"}
                  onClick={handleToggleReady}
                  disabled={!me || snapshot.session.status !== "LOBBY" || readySubmitting}
                >
                  {readySubmitting
                    ? "Saving..."
                    : me?.is_ready
                      ? "Mark Not Ready"
                      : "Mark Ready"}
                </Button>

                {isHost && (
                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={handleStartSession}
                    disabled={
                      snapshot.session.status !== "LOBBY" ||
                      !snapshot.session.all_ready ||
                      startSubmitting
                    }
                  >
                    {startSubmitting ? "Starting..." : "Start Session"}
                  </Button>
                )}

                <Button variant="text" onClick={() => navigate("/multiplayer")}>
                  Join Another Lobby
                </Button>
              </Stack>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Session Status
              </Typography>
              <Stack spacing={1}>
                <Typography variant="body2" color="text.secondary">
                  Phase: {snapshot.session.current_phase}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Turn: {snapshot.session.turn_number}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Status: {snapshot.session.status}
                </Typography>
              </Stack>
            </CardContent>
          </Card>

          {snapshot.state.phase && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Live Game Snapshot
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  The game has started. This panel reflects the server-authoritative snapshot coming over the session websocket.
                </Typography>

                <Stack spacing={1} sx={{ mb: 2 }}>
                  <Typography variant="body2">Current Phase: {snapshot.state.phase}</Typography>
                  <Typography variant="body2">Turn Number: {snapshot.state.turn_number ?? snapshot.session.turn_number}</Typography>
                </Stack>

                {snapshot.state.players && snapshot.state.players.length > 0 && (
                  <>
                    <Divider sx={{ mb: 2 }} />
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      Active Players
                    </Typography>
                    <List disablePadding>
                      {snapshot.state.players.map((player) => (
                        <ListItem key={player.display_name} disablePadding sx={{ py: 0.5 }}>
                          <ListItemText
                            primary={player.display_name}
                            secondary={player.is_alive ? "Alive" : "Eliminated"}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}

                {snapshot.state.events && snapshot.state.events.length > 0 && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      Event Log
                    </Typography>
                    <List disablePadding>
                      {snapshot.state.events.slice(-6).map((event) => (
                        <ListItem key={event} disablePadding sx={{ py: 0.5 }}>
                          <ListItemText primary={event} primaryTypographyProps={{ variant: "body2" }} />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </Stack>
      </Box>

      <Snackbar
        open={Boolean(actionError || actionNotice)}
        autoHideDuration={4000}
        onClose={() => {
          setActionError(null);
          setActionNotice(null);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={actionError ? "error" : "success"}
          onClose={() => {
            setActionError(null);
            setActionNotice(null);
          }}
          sx={{ width: "100%" }}
        >
          {actionError || actionNotice}
        </Alert>
      </Snackbar>
    </Box>
  );
}
