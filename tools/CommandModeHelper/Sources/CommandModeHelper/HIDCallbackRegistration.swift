import Foundation

@MainActor
final class HIDCallbackRegistration {
    private let context: UnsafeMutableRawPointer
    private let registerInput: (UnsafeMutableRawPointer) -> Void
    private let registerRemoval: (UnsafeMutableRawPointer) -> Void
    private let unregisterInput: (UnsafeMutableRawPointer) -> Void
    private let unregisterRemoval: (UnsafeMutableRawPointer) -> Void
    private var installed = false

    init(context: UnsafeMutableRawPointer,
         registerInput: @escaping (UnsafeMutableRawPointer) -> Void,
         registerRemoval: @escaping (UnsafeMutableRawPointer) -> Void,
         unregisterInput: @escaping (UnsafeMutableRawPointer) -> Void,
         unregisterRemoval: @escaping (UnsafeMutableRawPointer) -> Void) {
        self.context = context
        self.registerInput = registerInput
        self.registerRemoval = registerRemoval
        self.unregisterInput = unregisterInput
        self.unregisterRemoval = unregisterRemoval
    }

    func install() {
        guard !installed else { return }
        registerInput(context)
        registerRemoval(context)
        installed = true
    }

    func remove() {
        guard installed else { return }
        unregisterInput(context)
        unregisterRemoval(context)
        installed = false
    }
}
