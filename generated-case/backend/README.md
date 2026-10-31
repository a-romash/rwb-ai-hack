# Backend skeleton

Generic ASP.NET Core 10 (`net10.0`, C# 14) modular monolith with no business domain. The generator fills it in later.

`src/App.Api/Features/Generated/` is overwritten by the generator.
`src/App.Domain/Hooks/` and `src/App.Api/Features/Custom/` are not.

Time comes from `TimeProvider`. `DateTime.Now`, `DateTime.UtcNow`, and `Console.WriteLine` are banned.

Build from this folder with the .NET 10 SDK: `dotnet build App.sln`.
