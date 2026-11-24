import SwiftUI

struct AboutView: View {
    @State private var taps = 0

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("SimSample")
                    .font(.largeTitle)
                Text("A small sample app for the ollama-ios-simulator-agent. It has a task list, a detail screen, and this About tab, so the simulator agent has more than one screen to describe.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                Button("Tap count: \(taps)") {
                    taps += 1
                }
                .buttonStyle(.borderedProminent)
                Spacer()
            }
            .padding()
            .navigationTitle("About")
        }
    }
}
