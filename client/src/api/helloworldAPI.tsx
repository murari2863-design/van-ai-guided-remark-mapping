import { apiURL } from "../data/settings";
import { parseJSON } from "./utils";

const helloworldUrl = apiURL + "/helloworld";

const helloworldAPI = {
  getHelloWorld() {
    const options: RequestInit = {
      method: "GET",
      credentials: "include",
    };
    return fetch(`${helloworldUrl}`, options)
      .then(parseJSON)
      .catch((error) => {
        console.log("log client error " + error);
        throw new Error("There was a client error during the login process.");
      });
  },
};


export { helloworldAPI };
