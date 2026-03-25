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
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Snackbar from "@mui/material/Snackbar";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useAuth } from "../contexts/AuthContext";
import { getWebSocketSessionUrl } from "../services/api";
import {
  getSessionSnapshot,
  setSessionReady,
  startSession,
  submitSessionVote,
} from "../services/sessions";
import type { SessionParticipant, SessionSnapshot, SessionSocketMessage } from "../types";

type SocketStatus = "connecting" | "connected" | "disconnected";

function getParticipantStatus(
  participant: SessionParticipant,
  snapshot: SessionSnapshot,
  submittedParticipantIds: number[],
) {
  if (snapshot.session.status === "LOBBY") {
    if (!participant.is_connected) {
      return { label: "Offline", color: "default" as const };
    }
    if (participant.is_ready) {
      return { label: "Ready", color: "success" as const };
    }
    return { label: "Waiting", color: "warning" as const };
  }

  if (!participant.is_alive) {
    return { label: "Eliminated", color: "default" as const };
  }

  if (
    snapshot.session.current_phase === "VOTING" &&
    submittedParticipantIds.includes(participant.id)
  ) {
    return { label: "Vote Locked", color: "success" as const };
  }

  if (!participant.is_connected) {
    return { label: "Offline", color: "default" as const };
  }

  return { label: "Alive", color: "primary" as const };
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
  const [voteSubmitting, setVoteSubmitting] = useState(false);
  const [selectedVoteTargetId, setSelectedVoteTargetId] = useState<number>(0);

  useEffect(() => {
    if (!Number.isFinite(numericSessionId)) {
      setError("That session link is invalid.");
      setLoading(false);
      return;
    }

    let active = true;

    getSessionSnapshot(numericSessionId)
      .then((data) => {
        if (!active) {
          return;
        }
        setSnapshot(data);
        setLoading(false);
      })
      .catch((err: any) => {
        if (!active) {
          return;
        }
        const message =
          err?.response?.data?.error || "Unable to load this session right now.";
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

  const me = snapshot?.me ?? null;
  const isHost = snapshot?.session.host_user_id === user?.id;
  const submittedParticipantIds =
    snapshot?.state.vote_state?.submitted_participant_ids ?? [];
  const aliveParticipants = useMemo(
    () => snapshot?.participants.filter((participant) => participant.is_alive) ?? [],
    [snapshot],
  );
  const availableVoteTargets = useMemo(() => {
    if (!snapshot || !me) {
      return [];
    }

    const allowedIds = new Set(me.available_vote_target_ids);
    const preferredTargets = snapshot.participants.filter(
      (participant) =>
        allowedIds.has(participant.id) && participant.id !== me.participant_id,
    );
    if (preferredTargets.length > 0) {
      return preferredTargets;
    }

    return snapshot.participants.filter((participant) => allowedIds.has(participant.id));
  }, [snapshot, me]);

  useEffect(() => {
    if (availableVoteTargets.length === 0) {
      setSelectedVoteTargetId(0);
      return;
    }

    if (!availableVoteTargets.some((participant) => participant.id === selectedVoteTargetId)) {
      setSelectedVoteTargetId(availableVoteTargets[0].id);
    }
  }, [availableVoteTargets, selectedVoteTargetId]);

  const handleToggleReady = async () => {
    if (!snapshot || !me) {
      return;
    }

    setReadySubmitting(true);
    setActionError(null);
    try {
      const updated = await setSessionReady(snapshot.session.id, !snapshot.participants.find(
        (participant) => participant.id === me.participant_id,
      )?.is_ready);
      setSnapshot(updated);
      setActionNotice(
        updated.participants.find((participant) => participant.id === me.participant_id)?.is_ready
          ? "You are marked ready."
          : "You are marked not ready.",
      );
    } catch (err: any) {
      const message =
        err?.response?.data?.error || "Unable to update your ready state right now.";
      setActionError(message);
    } finally {
      setReadySubmitting(false);
    }
  };

  const handleStartSession = async () => {
    if (!snapshot) {
      return;
    }

    setStartSubmitting(true);
    setActionError(null);
    try {
      const updated = await startSession(snapshot.session.id);
      setSnapshot(updated);
      setActionNotice("The live voting session has started.");
    } catch (err: any) {
      const message =
        err?.response?.data?.error || "Unable to start the session right now.";
      setActionError(message);
    } finally {
      setStartSubmitting(false);
    }
  };

  const handleSubmitVote = async () => {
    if (!snapshot || !me || !selectedVoteTargetId) {
      return;
    }

    setVoteSubmitting(true);
    setActionError(null);
    try {
      const updated = await submitSessionVote(snapshot.session.id, selectedVoteTargetId);
      setSnapshot(updated);
      setActionNotice("Your vote has been locked in.");
    } catch (err: any) {
      const message =
        err?.response?.data?.error || "Unable to submit your vote right now.";
      setActionError(message);
    } finally {
      setVoteSubmitting(false);
    }
  };

  const handleCopyJoinCode = async () => {
    if (!snapshot) {
      return;
    }

    try {
      await navigator.clipboard.writeText(snapshot.session.join_code);
      setActionNotice("Join code copied to clipboard.");
    } catch {
      setActionError("Unable to copy the join code from this browser.");
    }
  };

  if (loading) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center", flexGrow: 1 }}
      >
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

  const myParticipant = snapshot.participants.find(
    (participant) => participant.id === me?.participant_id,
  );
  const hasSubmittedVote = Boolean(me?.has_submitted_vote);
  const liveVoteState = snapshot.state.vote_state;
  const lastResult = liveVoteState?.last_result;

  return (
    <Box
      sx={{
        p: 4,
        maxWidth: 1180,
        mx: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 3,
      }}
    >
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

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
            alignItems={{ xs: "stretch", sm: "center" }}
          >
            <Chip
              label={`Socket: ${socketStatus}`}
              color={
                socketStatus === "connected"
                  ? "success"
                  : socketStatus === "connecting"
                    ? "warning"
                    : "default"
              }
            />
            <Chip label={`Code: ${snapshot.session.join_code}`} color="secondary" />
            <Button variant="outlined" onClick={handleCopyJoinCode}>
              Copy Join Code
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "1.15fr 0.85fr" },
          gap: 3,
        }}
      >
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Player Roster
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {snapshot.session.status === "LOBBY"
                ? `${snapshot.session.ready_count} of ${snapshot.session.participant_count} players ready`
                : `${submittedParticipantIds.length} of ${aliveParticipants.length} living players have locked a vote this round`}
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <List disablePadding>
              {snapshot.participants.map((participant) => {
                const status = getParticipantStatus(
                  participant,
                  snapshot,
                  submittedParticipantIds,
                );
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
                          : `${participant.username}${participant.is_alive ? "" : " - Revealed on elimination"}`
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
                  Runtime: {snapshot.state.mode || "Lobby"}
                </Typography>
              </Stack>

              {snapshot.session.status !== "LOBBY" && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  This multiplayer MVP is running server-authoritative live voting rounds. Every client view is refreshed from the same session snapshot.
                </Alert>
              )}
            </CardContent>
          </Card>

          {me && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  You
                </Typography>
                <Stack spacing={1}>
                  <Typography variant="body2">{me.display_name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Role: {me.role_name || "Hidden until the session starts"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Alignment: {me.role_alignment || "Hidden until the session starts"}
                  </Typography>
                  <Typography
                    variant="body2"
                    color={me.is_alive ? "success.main" : "error.main"}
                    fontWeight={600}
                  >
                    {me.is_alive ? "Alive" : "Eliminated"}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          )}

          {snapshot.session.status === "LOBBY" ? (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Lobby Controls
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Ready up while the lobby is open. Once everyone is set, the host can launch the live session.
                </Typography>

                <Stack spacing={1.5}>
                  <Button
                    variant={myParticipant?.is_ready ? "outlined" : "contained"}
                    color={myParticipant?.is_ready ? "warning" : "success"}
                    onClick={handleToggleReady}
                    disabled={!myParticipant || readySubmitting}
                  >
                    {readySubmitting
                      ? "Saving..."
                      : myParticipant?.is_ready
                        ? "Mark Not Ready"
                        : "Mark Ready"}
                  </Button>

                  {isHost && (
                    <Button
                      variant="contained"
                      color="secondary"
                      onClick={handleStartSession}
                      disabled={!snapshot.session.all_ready || startSubmitting}
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
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Vote Panel
                </Typography>
                {!me?.is_alive ? (
                  <Typography variant="body2" color="text.secondary">
                    You have been eliminated, so this round is view-only from here.
                  </Typography>
                ) : snapshot.session.current_phase === "GAME_OVER" ? (
                  <Typography variant="body2" color="text.secondary">
                    The session is over. Review the latest result and event log below.
                  </Typography>
                ) : hasSubmittedVote ? (
                  <Alert severity="success">
                    Your vote is locked in. Waiting for the rest of the living players to finish this round.
                  </Alert>
                ) : (
                  <Stack spacing={2}>
                    <Typography variant="body2" color="text.secondary">
                      Pick one living player. The server resolves the round as soon as every living participant has submitted a vote.
                    </Typography>
                    <FormControl fullWidth>
                      <InputLabel id="vote-target-label">Vote Target</InputLabel>
                      <Select
                        labelId="vote-target-label"
                        value={selectedVoteTargetId || ""}
                        label="Vote Target"
                        onChange={(event) => setSelectedVoteTargetId(Number(event.target.value))}
                        disabled={voteSubmitting || availableVoteTargets.length === 0}
                      >
                        {availableVoteTargets.map((participant) => (
                          <MenuItem key={participant.id} value={participant.id}>
                            {participant.display_name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Button
                      variant="contained"
                      color="error"
                      onClick={handleSubmitVote}
                      disabled={
                        voteSubmitting ||
                        availableVoteTargets.length === 0 ||
                        !selectedVoteTargetId
                      }
                    >
                      {voteSubmitting ? "Submitting..." : "Lock In Vote"}
                    </Button>
                  </Stack>
                )}
              </CardContent>
            </Card>
          )}

          {lastResult && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Last Resolution
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {lastResult.outcome_message}
                </Typography>
                <List disablePadding>
                  {lastResult.vote_counts.map((entry) => (
                    <ListItem key={entry.target_participant_id} disablePadding sx={{ py: 0.5 }}>
                      <ListItemText
                        primary={entry.target_display_name}
                        secondary={`${entry.count} vote${entry.count === 1 ? "" : "s"}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}
        </Stack>
      </Box>

      {snapshot.state.events && snapshot.state.events.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Event Log
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Recent server events for this live session.
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <List disablePadding>
              {snapshot.state.events.slice(-10).map((event) => (
                <ListItem key={event} disablePadding sx={{ py: 0.5 }}>
                  <ListItemText primary={event} primaryTypographyProps={{ variant: "body2" }} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

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
