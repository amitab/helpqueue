import React, { useState, useEffect } from "react";
import { Container, Button, Input, Label, Card, Form, Select } from "semantic-ui-react";
import useLogin from "../hooks/useLogin";
import { User } from "./Types";
import ServerHelper, { ServerURL } from "./ServerHelper";
import useViewer from "../hooks/useViewer";
import TagsInput from "react-tagsinput";
import "react-tagsinput/react-tagsinput.css"; // If using WebPack and style-loader.
import { useCookies } from "react-cookie";
import createAlert, { AlertType } from "./Alert";
import { Alert, Badge } from "reactstrap";

const ProfilePage = () => {
  const { getCredentials } = useLogin();
  const [_cookies, setCookie] = useCookies();
  const { isLoggedIn } = useViewer();
  const { settings } = useViewer();
  const [user, setUser] = useState<User | null>(null);
  const [name, setName] = useState("");
  const [team, setTeam] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [permissionsGranted, setPermissionsGranted] = useState(true);
  const teamOptions = ((settings && settings.teams) || "no team")
      .split(",")
      .map((l) => ({ key: l, value: l, text: l }));

  const getUser = async () => {
    const res = await ServerHelper.post(ServerURL.userTicket, getCredentials());
    if (res.success) {
      setUser(res.user);
      setName(res.user.name || "");
      setTeam(res.user.team || "");
    } else {
      setUser(null);
      createAlert(AlertType.Error, "Failed to get user, are you logged in?");
    }
  };
  const saveProfile = async (shouldRedirect: string | null) => {
    if (name.length === 0) {
      createAlert(AlertType.Error, "Name must be nonempty");
      return;
    }
    const res = await ServerHelper.post(ServerURL.userUpdate, {
      ...getCredentials(),
      name: name,
      team: team,
      affiliation: "", // TODO(kevinfang): add company affiliation
      skills: skills.join(";"),
    });
    if (res.success) {
      setUser(res.user);
      createAlert(AlertType.Success, "Updated profile");
    } else {
      setUser(null);
      createAlert(AlertType.Error, "Failed to update profile");
    }
    if (shouldRedirect) {
      window.location.href = shouldRedirect;
    }
  };

  useEffect(() => {
    getUser();
    if (Notification) {
      Notification.requestPermission();
    }
  }, []);
  const permission = Notification && Notification.permission;

  useEffect(() => {
    if (Notification && permission !== "granted") {
      setPermissionsGranted(false);
    }
  }, [permission]);

  const tempName = user ? user.name : null;
  const tempSkills = user ? user.skills : null;
  useEffect(() => {
    if (tempName) {
      setName(tempName);
      setCookie("name", tempName);
    }
    if (tempSkills) {
      setSkills(tempSkills.split(";").filter((e) => e.length > 0));
    }
  }, [tempName, tempSkills]);

  if (!isLoggedIn) {
    window.location.href = "/login";
  }

  if (!user) {
    return (
      <div>
        <p style={{ color: "white" }}>Loading user...</p>
      </div>
    );
  }

  return (
    <Container>
      <Card>
        <h2> Profile </h2>
        <Form>
          <Form.Field>
            <Input
              label="Display Name:"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Form.Field>
          <Form.Field>
            <Input
              disabled
              label="Email:"
              value={user.email}
              readOnly
              className="text-center"
            />
          </Form.Field>
          {!user.mentor_is ? (
            <>
              <Form.Field required>
                <label>Team Name:</label>
                <Select
                  value={team}
                  options={teamOptions}
                  onChange={(_e, data) => setTeam("" + data.value || "")}
                />
              </Form.Field>
            </>
          ) : null}
        </Form>
        <br />
        {user.mentor_is ? (
          <>
            <Label>
              Technical skills (i.e. javascript, java...):
              <TagsInput value={skills} onChange={(e) => setSkills(e)} />
            </Label>
          </>
        ) : null}
        <br />
        {!permissionsGranted
          ? <Alert color="warning">You have not enabled desktop notifications! Consider enabling them! Look at the top left corner</Alert>
          : null}
        <div>
          <Button onClick={() => saveProfile(null)}>Save Profile</Button>
          {!user.mentor_is || user.admin_is ? (
            <Button
              color="blue"
              onClick={() => {
                saveProfile("/");
              }}
            >
              Go to Queue!
            </Button>
          ) : null}
          {user.mentor_is || user.admin_is ? (
            <Button
              color="blue"
              onClick={() => {
                saveProfile("/m");
              }}
            >
              Go to Mentor Queue!
            </Button>
          ) : null}
        </div>
      </Card>
    </Container>
  );
};

export default ProfilePage;
