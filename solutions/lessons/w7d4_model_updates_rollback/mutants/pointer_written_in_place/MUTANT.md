# pointer_written_in_place

The pointer file is rewritten in place. A crash between truncation and write leaves an empty pointer and a service that cannot start; the move is also not covered by os.replace.
