# Built by infra/docker-compose.yml with `network: none`: the sandbox restore step (pack.json)
# has already filled .nuget and obj/, at the same /work paths, so publishing needs no network.
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
ENV NUGET_PACKAGES=/work/.nuget/packages DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
WORKDIR /work
COPY .nuget/ .nuget/
COPY backend/ backend/
RUN dotnet publish backend/src/App.Api/App.Api.csproj -c Release --no-restore -o /out/api \
 && dotnet publish backend/src/App.Worker/App.Worker.csproj -c Release --no-restore -o /out/worker

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS api
WORKDIR /app
COPY --from=build /out/api .
USER app
EXPOSE 8080
ENTRYPOINT ["dotnet", "App.Api.dll"]

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS worker
WORKDIR /app
COPY --from=build /out/worker .
USER app
ENTRYPOINT ["dotnet", "App.Worker.dll"]
