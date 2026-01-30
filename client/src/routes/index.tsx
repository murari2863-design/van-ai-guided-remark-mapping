import { createFileRoute } from "@tanstack/react-router";
import TaxonomyClassifier from "../integrations/TaxonomyClassifier";



export const Route = createFileRoute("/")({
  component: App,
});

function App() {
  return (
    <div className="min-h-screen bg-slate-100">
      <TaxonomyClassifier />
    </div>
  );
}


/*import { createFileRoute } from "@tanstack/react-router";

import { helloworldAPI } from "@/api/helloworldAPI";
import { useQuery } from "@tanstack/react-query";

export const Route = createFileRoute("/")({
  component: App,
});

function App() {
  const { data, error, isFetching } = useQuery({
    queryKey: ["helloworld"],
    queryFn: () => helloworldAPI.getHelloWorld(),
    enabled: true,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
    refetchOnMount: false,
    retry: 1,
  });

  return (
    <div className="text-center min-h-screen flex">
      <div
        className="flex-1 text-white"
        style={{
          background: "linear-gradient(135deg, #000000 60%, #02012f 100%)",
        }}
      >
        {isFetching ? "Loading..." : data ? data.message : `Error: ${error}`}
      </div>
    </div>
  );
}
*/





